import argparse
import json
import logging
import os
import re
import time
from notion_client import Client
import requests
from requests.utils import cookiejar_from_dict
from http.cookies import SimpleCookie
from datetime import datetime
import hashlib
from dotenv import load_dotenv
from retrying import retry
from utils import (
    get_callout,
    get_date,
    get_file,
    get_heading,
    get_icon,
    get_multi_select,
    get_number,
    get_quote,
    get_rich_text,
    get_select,
    get_table_of_contents,
    get_title,
    get_url,
    get_status,
    get_relation,
)

load_dotenv()

# 微信读书 API URLs
WEREAD_URL = "https://weread.qq.com/"
WEREAD_NOTEBOOKS_URL = "https://weread.qq.com/api/user/notebook"
WEREAD_BOOKMARKLIST_URL = "https://weread.qq.com/web/book/bookmarklist"
WEREAD_CHAPTER_INFO = "https://weread.qq.com/web/book/chapterInfos"
WEREAD_READ_INFO_URL = "https://weread.qq.com/web/book/readinfo"
WEREAD_REVIEW_LIST_URL = "https://weread.qq.com/web/review/list"
WEREAD_BOOK_INFO = "https://weread.qq.com/web/book/info"

# Notion 数据库 ID (从环境变量或直接配置)
# 书籍数据库: collection://2bbdd161-f4eb-8186-a76d-000b09f5ad17
# 笔记数据库: collection://2bbdd161-f4eb-811b-a16a-000b87a9fd3b
# 信息数据库: collection://2bbdd161-f4eb-8101-9bfd-000b703c3623
BOOK_DATABASE_ID = os.getenv("BOOK_DATABASE_ID", "2bbdd161f4eb81e596d4c922546f1086")
NOTE_DATABASE_ID = os.getenv("NOTE_DATABASE_ID", "2bbdd161f4eb813fa96deee0a105c004")
INFO_DATABASE_ID = os.getenv("INFO_DATABASE_ID", "2bbdd161f4eb8141bf2ee02d3a908745")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
if not NOTION_TOKEN:
    raise Exception("NOTION_TOKEN 环境变量未设置，请按照文档配置")

def parse_cookie_string(cookie_string):
    cookie = SimpleCookie()
    cookie.load(cookie_string)
    cookies_dict = {}
    cookiejar = None
    for key, morsel in cookie.items():
        cookies_dict[key] = morsel.value
        cookiejar = cookiejar_from_dict(cookies_dict, cookiejar=None, overwrite=True)
    return cookiejar


def refresh_token(exception):
    session.get(WEREAD_URL)


@retry(stop_max_attempt_number=3, wait_fixed=5000, retry_on_exception=refresh_token)
def get_bookmark_list(bookId):
    """获取我的划线"""
    session.get(WEREAD_URL)
    params = dict(bookId=bookId)
    r = session.get(WEREAD_BOOKMARKLIST_URL, params=params)
    if r.ok:
        updated = r.json().get("updated", [])
        if updated:
            updated = sorted(
                updated,
                key=lambda x: (x.get("chapterUid", 1), int(x.get("range", "0-0").split("-")[0] or 0)),
            )
        return updated
    return []


@retry(stop_max_attempt_number=3, wait_fixed=5000, retry_on_exception=refresh_token)
def get_read_info(bookId):
    session.get(WEREAD_URL)
    params = dict(bookId=bookId, readingDetail=1, readingBookIndex=1, finishedDate=1)
    r = session.get(WEREAD_READ_INFO_URL, params=params)
    if r.ok:
        return r.json()
    return None


@retry(stop_max_attempt_number=3, wait_fixed=5000, retry_on_exception=refresh_token)
def get_bookinfo(bookId):
    """获取书的详情"""
    session.get(WEREAD_URL)
    params = dict(bookId=bookId)
    r = session.get(WEREAD_BOOK_INFO, params=params)
    if r.ok:
        data = r.json()
        isbn = data.get("isbn", "")
        newRating = data.get("newRating", 0) / 100  # 转换为0-10分制
        intro = data.get("intro", "")
        return (isbn, newRating, intro)
    else:
        print(f"获取 {bookId} 书籍信息失败")
        return ("", 0, "")


@retry(stop_max_attempt_number=3, wait_fixed=5000, retry_on_exception=refresh_token)
def get_review_list(bookId):
    """获取笔记（点评）"""
    session.get(WEREAD_URL)
    params = dict(bookId=bookId, listType=11, mine=1, syncKey=0)
    r = session.get(WEREAD_REVIEW_LIST_URL, params=params)
    if r.ok:
        reviews = r.json().get("reviews", [])
        # type=4 是书评/点评, type=1 是段落笔记
        summary = list(filter(lambda x: x.get("review", {}).get("type") == 4, reviews))
        notes = list(filter(lambda x: x.get("review", {}).get("type") == 1, reviews))
        notes = list(map(lambda x: x.get("review"), notes))
        return summary, notes
    return [], []


@retry(stop_max_attempt_number=3, wait_fixed=5000, retry_on_exception=refresh_token)
def get_chapter_info(bookId):
    """获取章节信息"""
    session.get(WEREAD_URL)
    body = {"bookIds": [bookId], "synckeys": [0], "teenmode": 0}
    r = session.post(WEREAD_CHAPTER_INFO, json=body)
    if (
        r.ok
        and "data" in r.json()
        and len(r.json()["data"]) == 1
        and "updated" in r.json()["data"][0]
    ):
        update = r.json()["data"][0]["updated"]
        return {item["chapterUid"]: item for item in update}
    return None


def check_book_exists(bookId):
    """检查书籍是否已存在，返回页面ID或None"""
    # 通过书籍ID字段精确匹配
    filter = {
        "property": "书籍ID",
        "rich_text": {"equals": bookId}
    }
    response = client.databases.query(database_id=BOOK_DATABASE_ID, filter=filter)
    if response.get("results"):
        return response["results"][0]["id"]
    return None


def get_book_status(book_page_id):
    """
    获取书籍在Notion中的状态
    
    Args:
        book_page_id: 书籍页面ID（str）
    
    Returns:
        str or None: 书籍状态（"已经读完"、"正在阅读"、"计划阅读"），如果获取失败返回None
    """
    if not book_page_id:
        return None
    
    try:
        # 获取页面属性
        page = client.pages.retrieve(page_id=book_page_id)
        properties = page.get("properties", {})
        
        # 获取状态字段
        status_property = properties.get("状态", {})
        status = status_property.get("status", {})
        
        if status:
            status_name = status.get("name", "")
            return status_name
        
        return None
    except Exception as e:
        # 如果获取失败，记录错误但不影响主流程
        print(f"    ⚠️  获取书籍状态时出错: {e}")
        return None


def get_weread_status(read_info):
    """
    获取微信读书的阅读状态
    
    Args:
        read_info: 微信读书阅读信息（dict）
    
    Returns:
        str or None: 阅读状态（"已经读完"、"正在阅读"、"计划阅读"），如果获取失败返回None
    """
    if not read_info:
        return None
    
    marked_status = read_info.get("markedStatus", 0)
    
    if marked_status == 4:
        return "已经读完"
    elif marked_status > 0:
        return "正在阅读"
    else:
        return "计划阅读"


def normalize_text_for_title(text):
    """
    规范化文本用于Notion标题（笔记和划线）
    严格按照以下步骤处理：
    1. 类型检查和空值处理
    2. 将换行符替换为空格（\r\n, \n, \r）
    3. 去除首尾空格
    4. 将多个连续空格合并为单个空格（包括制表符等空白字符）
    5. 截断到标题最大长度（300字符）
    
    Args:
        text: 原始文本（str或None）
    
    Returns:
        str: 规范化后的文本，如果输入为空则返回空字符串
    """
    # 类型检查和空值处理
    if text is None:
        return ""
    
    # 确保是字符串类型
    if not isinstance(text, str):
        text = str(text)
    
    # 如果为空字符串或只包含空白字符，返回空字符串
    if not text.strip():
        return ""
    
    # 步骤1: 替换所有类型的换行符为空格
    # 先处理 \r\n（Windows换行），再处理单独的 \n 和 \r
    normalized = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    
    # 步骤2: 去除首尾空格
    normalized = normalized.strip()
    
    # 步骤3: 将多个连续空白字符（空格、制表符等）合并为单个空格
    # \s+ 匹配一个或多个空白字符（包括空格、制表符、换行符等）
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # 步骤4: 笔记和划线的标题限制为300字符
    TITLE_MAX_LENGTH = 300
    if len(normalized) > TITLE_MAX_LENGTH:
        normalized = normalized[:TITLE_MAX_LENGTH]
    
    return normalized


def check_note_exists(note_content, book_page_id):
    """
    严格检查笔记是否已存在
    通过规范化后的笔记内容（名称）和关联的书籍来判断
    使用统一的文本规范化处理，确保插入和检查逻辑一致
    
    Args:
        note_content: 笔记内容（str）
        book_page_id: 书籍页面ID（str）
    
    Returns:
        str or None: 如果找到已存在的笔记，返回页面ID；否则返回None
    """
    # 严格检查输入参数
    if not note_content or not book_page_id:
        return None
    
    # 规范化文本（与insert_note_to_notion保持一致）
    normalized_title = normalize_text_for_title(note_content)
    
    # 如果规范化后为空，说明笔记内容无效，返回None
    if not normalized_title:
        return None
    
    # 复合过滤器：名称精确匹配且关联到同一本书
    filter_condition = {
        "and": [
            {
                "property": "名称",
                "title": {"equals": normalized_title}
            },
            {
                "property": "书籍",
                "relation": {"contains": book_page_id}
            }
        ]
    }
    
    try:
        response = client.databases.query(
            database_id=NOTE_DATABASE_ID,
            filter=filter_condition
        )
        results = response.get("results", [])
        if results:
            # 找到匹配的笔记，返回页面ID
            return results[0]["id"]
    except Exception as e:
        # 如果查询失败，记录错误但不影响主流程
        print(f"    ⚠️  检查笔记是否存在时出错: {e}")
    
    return None


def check_info_exists(highlight_text, book_page_id):
    """
    严格检查划线是否已存在
    通过规范化后的划线文本（名称）和关联的书籍来判断
    避免不同书籍有相同划线文本时误判
    使用统一的文本规范化处理，确保插入和检查逻辑一致
    
    Args:
        highlight_text: 划线文本（str）
        book_page_id: 书籍页面ID（str）
    
    Returns:
        str or None: 如果找到已存在的划线，返回页面ID；否则返回None
    """
    # 严格检查输入参数
    if not highlight_text or not book_page_id:
        return None
    
    # 规范化文本（与insert_highlight_to_info保持一致）
    normalized_title = normalize_text_for_title(highlight_text)
    
    # 如果规范化后为空，说明划线文本无效，返回None
    if not normalized_title:
        return None
    
    # 复合过滤器：名称精确匹配且关联到同一本书
    filter_condition = {
        "and": [
            {
                "property": "名称",
                "title": {"equals": normalized_title}
            },
            {
                "property": "书籍",
                "relation": {"contains": book_page_id}
            }
        ]
    }
    
    try:
        response = client.databases.query(
            database_id=INFO_DATABASE_ID,
            filter=filter_condition
        )
        results = response.get("results", [])
        if results:
            # 找到匹配的划线，返回页面ID
            return results[0]["id"]
    except Exception as e:
        # 如果查询失败，记录错误但不影响主流程
        print(f"    ⚠️  检查划线是否存在时出错: {e}")
    
    return None


def extract_reading_progress(read_info):
    """
    从微信读书的read_info中提取阅读进度
    返回0-1之间的小数（Notion百分比格式要求）
    """
    if not read_info:
        return None
    
    # 尝试多种可能的字段路径
    percentage = None
    
    # 1. 直接在根级别
    if "percentage" in read_info:
        percentage = read_info.get("percentage")
    # 2. 在readingDetail中
    if percentage is None and "readingDetail" in read_info:
        reading_detail = read_info.get("readingDetail", {})
        if isinstance(reading_detail, dict) and "percentage" in reading_detail:
            percentage = reading_detail.get("percentage")
    # 3. 在readingBookIndex中
    if percentage is None and "readingBookIndex" in read_info:
        reading_book_index = read_info.get("readingBookIndex", {})
        if isinstance(reading_book_index, dict) and "percentage" in reading_book_index:
            percentage = reading_book_index.get("percentage")
    
    if percentage is not None:
        # 如果percentage是0-100的整数，转换为0-1的小数
        if percentage > 1:
            percentage = percentage / 100.0
        # 确保在0-1范围内
        return max(0.0, min(1.0, float(percentage)))
    
    return None


def insert_book_to_notion(book_name, book_id, cover, author, isbn, rating, intro, read_info):
    """
    插入书籍到书籍数据库
    字段映射:
    - 名称 (title) ← book_name
    - 书籍作者 (text) ← author
    - 书籍简介 (text) ← intro
    - 书籍ID (text) ← book_id
    - ISBN (text) ← isbn
    - 书籍链接 (url) ← 微信读书链接
    - 书籍封面 (file) ← cover
    - 豆瓣评分 (number) ← rating (0-10)
    - 状态 (status) ← 计划阅读/正在阅读/已经读完
    - 添加日期 (date) ← 当前日期
    - 读完日期 (date) ← finishedDate
    - 阅读进度 (number) ← percentage (0-1)
    """
    if not cover or not cover.startswith("http"):
        cover = "https://www.notion.so/icons/book_gray.svg"
    
    # 构建微信读书链接
    weread_url = f"https://weread.qq.com/web/reader/{calculate_book_str_id(book_id)}"
    
    parent = {"database_id": BOOK_DATABASE_ID, "type": "database_id"}
    properties = {
        "名称": get_title(book_name),
        "书籍作者": get_rich_text(author or ""),
        "书籍简介": get_rich_text(intro or ""),
        "书籍ID": get_rich_text(book_id),
        "书籍链接": get_url(weread_url),
        "书籍封面": get_file(cover),
        "添加日期": get_date(datetime.now().strftime("%Y-%m-%d")),
    }
    
    # ISBN
    if isbn:
        properties["ISBN"] = get_rich_text(isbn)
    
    # 豆瓣评分
    if rating and rating > 0:
        properties["豆瓣评分"] = get_number(rating)
    
    # 阅读状态和阅读进度
    if read_info:
        marked_status = read_info.get("markedStatus", 0)
        if marked_status == 4:
            properties["状态"] = get_status("已经读完")
            # 读完日期
            if "finishedDate" in read_info:
                finished_date = datetime.utcfromtimestamp(read_info.get("finishedDate")).strftime("%Y-%m-%d")
                properties["读完日期"] = get_date(finished_date)
        elif marked_status > 0:
            properties["状态"] = get_status("正在阅读")
        else:
            properties["状态"] = get_status("计划阅读")
        
        # 提取阅读进度
        reading_progress = extract_reading_progress(read_info)
        if reading_progress is not None:
            properties["阅读进度"] = get_number(reading_progress)
    else:
        properties["状态"] = get_status("计划阅读")
    
    icon = get_icon(cover)
    response = client.pages.create(parent=parent, icon=icon, cover=icon, properties=properties)
    return response["id"]


def update_book_in_notion(page_id, book_name, book_id, cover, author, isbn, rating, intro, read_info):
    """更新已存在的书籍"""
    if not cover or not cover.startswith("http"):
        cover = "https://www.notion.so/icons/book_gray.svg"
    
    weread_url = f"https://weread.qq.com/web/reader/{calculate_book_str_id(book_id)}"
    
    properties = {
        "名称": get_title(book_name),
        "书籍作者": get_rich_text(author or ""),
        "书籍简介": get_rich_text(intro or ""),
        "书籍ID": get_rich_text(book_id),
        "书籍链接": get_url(weread_url),
        "书籍封面": get_file(cover),
    }
    
    # ISBN
    if isbn:
        properties["ISBN"] = get_rich_text(isbn)
    
    if rating and rating > 0:
        properties["豆瓣评分"] = get_number(rating)
    
    if read_info:
        marked_status = read_info.get("markedStatus", 0)
        if marked_status == 4:
            properties["状态"] = get_status("已经读完")
            if "finishedDate" in read_info:
                finished_date = datetime.utcfromtimestamp(read_info.get("finishedDate")).strftime("%Y-%m-%d")
                properties["读完日期"] = get_date(finished_date)
        elif marked_status > 0:
            properties["状态"] = get_status("正在阅读")
        
        # 提取并更新阅读进度
        reading_progress = extract_reading_progress(read_info)
        if reading_progress is not None:
            properties["阅读进度"] = get_number(reading_progress)
    
    icon = get_icon(cover)
    client.pages.update(page_id=page_id, icon=icon, cover=icon, properties=properties)
    return page_id


def insert_note_to_notion(note_content, book_page_id, chapter_title=None):
    """
    插入笔记到笔记数据库
    字段映射:
    - 名称 (title) ← note_content（规范化处理）
    - 日期 (date) ← 当前日期
    - 分类 (status) ← 文献笔记
    - 书籍 (relation) ← book_page_id
    
    Args:
        note_content: 笔记内容（str）
        book_page_id: 书籍页面ID（str）
        chapter_title: 章节标题（str，可选）
    
    Returns:
        str: 创建的笔记页面ID
    """
    # 规范化文本用于标题（与check_note_exists保持一致）
    title = normalize_text_for_title(note_content)
    
    # 严格检查：如果规范化后标题为空，抛出异常
    if not title:
        raise ValueError("笔记内容规范化后为空，无法创建笔记")
    
    if not book_page_id:
        raise ValueError("书籍页面ID不能为空")
    
    parent = {"database_id": NOTE_DATABASE_ID, "type": "database_id"}
    properties = {
        "名称": get_title(title),
        "日期": get_date(datetime.now().strftime("%Y-%m-%d")),
        "分类": get_status("文献笔记"),
    }
    
    # 关联书籍
    if book_page_id:
        properties["书籍"] = get_relation([book_page_id])
    
    response = client.pages.create(parent=parent, properties=properties)
    note_page_id = response["id"]
    
    # 添加完整内容到页面内容中
    if note_content:
        children = []
        if chapter_title:
            children.append(get_heading(3, f"章节：{chapter_title}"))
        
        # 分段添加内容
        for i in range(0, len(note_content), 2000):
            children.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": note_content[i:i+2000]}}]
                }
            })
        
        if children:
            add_children(note_page_id, children)
    
    return note_page_id


def insert_highlight_to_info(highlight_text, book_name, book_url, book_page_id, note_page_ids=None, chapter_title=None):
    """
    插入划线到信息数据库
    字段映射:
    - 名称 (title) ← highlight_text（规范化处理）
    - 类型 (select) ← 摘抄
    - 状态 (status) ← 收集
    - 网址 (url) ← book_url
    - 创建日期 (date) ← 当前日期
    - 笔记 (relation) ← note_page_ids
    - 书籍 (relation) ← book_page_id (双向关联到书籍库，反向字段名"信息")
    
    Args:
        highlight_text: 划线文本（str）
        book_name: 书籍名称（str）
        book_url: 书籍URL（str）
        book_page_id: 书籍页面ID（str）
        note_page_ids: 关联的笔记页面ID列表（list，可选）
        chapter_title: 章节标题（str，可选）
    
    Returns:
        str: 创建的划线页面ID
    """
    # 规范化文本用于标题（与check_info_exists保持一致）
    title = normalize_text_for_title(highlight_text)
    
    # 严格检查：如果规范化后标题为空，抛出异常
    if not title:
        raise ValueError("划线文本规范化后为空，无法创建划线")
    
    if not book_page_id:
        raise ValueError("书籍页面ID不能为空")
    
    parent = {"database_id": INFO_DATABASE_ID, "type": "database_id"}
    properties = {
        "名称": get_title(title),
        "类型": get_select("摘抄"),
        "状态": get_status("收集"),
        "创建日期": get_date(datetime.now().strftime("%Y-%m-%d")),
    }
    
    if book_url:
        properties["网址"] = get_url(book_url)
    
    # 关联笔记
    if note_page_ids:
        properties["笔记"] = get_relation(note_page_ids)
    
    # 关联书籍（双向关联，信息库字段名"书籍"，书籍库反向字段名"信息"）
    if book_page_id:
        properties["书籍"] = get_relation([book_page_id])
    
    response = client.pages.create(parent=parent, properties=properties)
    info_page_id = response["id"]
    
    # 添加完整内容到页面
    children = []
    if chapter_title:
        children.append(get_heading(3, f"来源：{book_name} - {chapter_title}"))
    else:
        children.append(get_heading(3, f"来源：{book_name}"))
    
    # 分段添加划线内容
    for i in range(0, len(highlight_text), 2000):
        children.append({
            "type": "quote",
            "quote": {
                "rich_text": [{"type": "text", "text": {"content": highlight_text[i:i+2000]}}],
                "color": "default"
            }
        })
    
    if children:
        add_children(info_page_id, children)
    
    return info_page_id


def add_children(id, children):
    """添加子块到页面"""
    results = []
    for i in range(0, len(children) // 100 + 1):
        batch = children[i * 100 : (i + 1) * 100]
        if not batch:
            continue
        time.sleep(0.3)
        response = client.blocks.children.append(block_id=id, children=batch)
        results.extend(response.get("results", []))
    return results


def get_notebooklist():
    """获取笔记本列表"""
    session.get(WEREAD_URL)
    r = session.get(WEREAD_NOTEBOOKS_URL)
    if r.ok:
        data = r.json()
        books = data.get("books", [])
        books.sort(key=lambda x: x["sort"])
        return books
    else:
        print(r.text)
    return None


def transform_id(book_id):
    id_length = len(book_id)

    if re.match("^\d*$", book_id):
        ary = []
        for i in range(0, id_length, 9):
            ary.append(format(int(book_id[i : min(i + 9, id_length)]), "x"))
        return "3", ary

    result = ""
    for i in range(id_length):
        result += format(ord(book_id[i]), "x")
    return "4", [result]


def calculate_book_str_id(book_id):
    md5 = hashlib.md5()
    md5.update(book_id.encode("utf-8"))
    digest = md5.hexdigest()
    result = digest[0:3]
    code, transformed_ids = transform_id(book_id)
    result += code + "2" + digest[-2:]

    for i in range(len(transformed_ids)):
        hex_length_str = format(len(transformed_ids[i]), "x")
        if len(hex_length_str) == 1:
            hex_length_str = "0" + hex_length_str

        result += hex_length_str + transformed_ids[i]

        if i < len(transformed_ids) - 1:
            result += "g"

    if len(result) < 20:
        result += digest[0 : 20 - len(result)]

    md5 = hashlib.md5()
    md5.update(result.encode("utf-8"))
    result += md5.hexdigest()[0:3]
    return result


def try_get_cloud_cookie(url, id, password):
    if url.endswith("/"):
        url = url[:-1]
    req_url = f"{url}/get/{id}"
    data = {"password": password}
    result = None
    response = requests.post(req_url, data=data)
    if response.status_code == 200:
        data = response.json()
        cookie_data = data.get("cookie_data")
        if cookie_data and "weread.qq.com" in cookie_data:
            cookies = cookie_data["weread.qq.com"]
            cookie_str = "; ".join(
                [f"{cookie['name']}={cookie['value']}" for cookie in cookies]
            )
            result = cookie_str
    return result


def get_cookie():
    url = os.getenv("CC_URL")
    if not url:
        url = "https://cookiecloud.malinkang.com/"
    id = os.getenv("CC_ID")
    password = os.getenv("CC_PASSWORD")
    cookie = os.getenv("WEREAD_COOKIE")
    if url and id and password:
        cookie = try_get_cloud_cookie(url, id, password)
    if not cookie or not cookie.strip():
        raise Exception("没有找到cookie，请按照文档填写cookie")
    return cookie


def sync_book(book_data):
    """同步单本书籍及其划线、笔记"""
    book = book_data.get("book")
    title = book.get("title")
    cover = book.get("cover", "").replace("/s_", "/t7_")
    book_id = book.get("bookId")
    author = book.get("author", "")
    
    print(f"  📖 正在处理书籍: {title}")
    
    # 检查书籍是否已存在
    existing_book_id = check_book_exists(book_id)
    
    # 获取微信读书的阅读信息
    read_info = get_read_info(book_id)
    weread_status = get_weread_status(read_info)
    
    # 如果书籍已存在，检查微信读书和Notion的状态
    if existing_book_id:
        notion_status = get_book_status(existing_book_id)
        
        # 只有当微信读书和Notion的状态都是"已经读完"时，才跳过同步
        if weread_status == "已经读完" and notion_status == "已经读完":
            print(f"    ⏭️  微信读书和Notion状态均为「已经读完」，跳过同步")
            return existing_book_id
    
    # 获取书籍详情（只有在需要同步时才获取）
    isbn, rating, intro = get_bookinfo(book_id)
    
    # 更新或创建书籍
    if existing_book_id:
        print(f"    ✓ 书籍已存在，更新中...")
        book_page_id = update_book_in_notion(
            existing_book_id, title, book_id, cover, author, isbn, rating, intro, read_info
        )
    else:
        print(f"    + 创建新书籍...")
        book_page_id = insert_book_to_notion(
            title, book_id, cover, author, isbn, rating, intro, read_info
        )
    
    # 构建微信读书链接
    book_url = f"https://weread.qq.com/web/reader/{calculate_book_str_id(book_id)}"
    
    # 获取章节信息
    chapter_info = get_chapter_info(book_id)
    
    # 获取划线列表
    bookmark_list = get_bookmark_list(book_id)
    print(f"    📝 发现 {len(bookmark_list)} 条划线")
    
    # 获取笔记（点评）
    summary, notes = get_review_list(book_id)
    print(f"    ✍️ 发现 {len(notes)} 条笔记, {len(summary)} 条书评")
    
    # 创建笔记页面（用于关联划线）
    note_page_ids = []
    note_count = 0
    
    # 处理书评（summary）- 作为笔记
    for item in summary:
        review = item.get("review", {})
        content = review.get("content", "")
        if content:
            # 严格检查笔记是否已存在（通过规范化内容和书籍关联）
            existing_note_id = check_note_exists(content, book_page_id)
            if existing_note_id:
                # 已存在的笔记，添加到关联列表但不再创建
                note_page_ids.append(existing_note_id)
                continue
            
            # 确认不存在，创建新笔记
            print(f"    + 添加书评笔记...")
            note_id = insert_note_to_notion(content, book_page_id, chapter_title="书评")
            note_page_ids.append(note_id)
            note_count += 1
            time.sleep(0.3)
    
    # 处理段落笔记 - 作为笔记
    for note in notes:
        content = note.get("content", "")
        chapter_uid = note.get("chapterUid", 1)
        chapter_title = None
        if chapter_info and chapter_uid in chapter_info:
            chapter_title = chapter_info[chapter_uid].get("title", "")
        
        if content:
            # 严格检查笔记是否已存在（通过规范化内容和书籍关联）
            existing_note_id = check_note_exists(content, book_page_id)
            if existing_note_id:
                # 已存在的笔记，添加到关联列表但不再创建
                note_page_ids.append(existing_note_id)
                continue
            
            # 确认不存在，创建新笔记
            print(f"    + 添加段落笔记...")
            note_id = insert_note_to_notion(content, book_page_id, chapter_title=chapter_title)
            note_page_ids.append(note_id)
            note_count += 1
            time.sleep(0.3)
    
    # 处理划线 - 作为信息
    highlight_count = 0
    skipped_count = 0
    for bookmark in bookmark_list:
        mark_text = bookmark.get("markText", "")
        if not mark_text:
            continue
        
        chapter_uid = bookmark.get("chapterUid", 1)
        chapter_title = None
        if chapter_info and chapter_uid in chapter_info:
            chapter_title = chapter_info[chapter_uid].get("title", "")
        
        # 严格检查是否已存在（通过规范化文本和关联的书籍）
        existing_info_id = check_info_exists(mark_text, book_page_id)
        if existing_info_id:
            # 已存在的划线，跳过
            skipped_count += 1
            continue
        
        # 确认不存在，创建新划线
        print(f"    + 添加划线到信息库...")
        insert_highlight_to_info(
            mark_text, title, book_url, book_page_id, 
            note_page_ids=note_page_ids if note_page_ids else None,
            chapter_title=chapter_title
        )
        highlight_count += 1
        time.sleep(0.3)
    
    # 输出统计信息
    total_highlights = len(bookmark_list)
    total_notes = len(notes) + len(summary)
    if total_highlights > 0:
        print(f"    ✓ 划线处理完成: 共 {total_highlights} 条，新增 {highlight_count} 条", end="")
        if skipped_count > 0:
            print(f"，跳过 {skipped_count} 条已存在的划线")
        else:
            print()
    if total_notes > 0:
        print(f"    ✓ 笔记处理完成: 共 {total_notes} 条，新增 {note_count} 条", end="")
        skipped_notes = total_notes - note_count
        if skipped_notes > 0:
            print(f"，跳过 {skipped_notes} 条已存在的笔记")
        else:
            print()
    return book_page_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="同步微信读书到Notion")
    parser.add_argument("--all", action="store_true", help="同步所有书籍，忽略已同步状态")
    options = parser.parse_args()
    
    print("=" * 50)
    print("微信读书 → Notion 同步工具")
    print("=" * 50)
    print(f"书籍数据库: {BOOK_DATABASE_ID}")
    print(f"笔记数据库: {NOTE_DATABASE_ID}")
    print(f"信息数据库: {INFO_DATABASE_ID}")
    print("=" * 50)
    
    weread_cookie = get_cookie()

    
    session = requests.Session()
    session.cookies = parse_cookie_string(weread_cookie)
    client = Client(auth=NOTION_TOKEN, log_level=logging.ERROR)
    
    session.get(WEREAD_URL)
    
    books = get_notebooklist()
    if books:
        print(f"\n📚 发现 {len(books)} 本书籍\n")
        
        for index, book_data in enumerate(books):
            print(f"\n[{index + 1}/{len(books)}]")
            try:
                sync_book(book_data)
            except Exception as e:
                print(f"    ❌ 同步失败: {e}")
                continue
            time.sleep(0.5)
        
        print("\n" + "=" * 50)
        print("✅ 同步完成!")
        print("=" * 50)
    else:
        print("❌ 未能获取书籍列表，请检查Cookie是否有效")
