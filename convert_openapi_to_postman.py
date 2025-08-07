# @Time:2025/7/24
# @Author:yong.huang@shopee.com

"""
OpenAPI 3.0.3 到 Postman Collection v2.1 转换器
"""

import json
import uuid
import re
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs


def convert_openapi_to_postman(openapi_file_path, output_file_path, custom_base_url=None):
    """
    将OpenAPI 3.0.3文件转换为Postman Collection v2.1格式
    
    Args:
        openapi_file_path: OpenAPI文件路径
        output_file_path: 输出文件路径
        custom_base_url: 自定义基础URL，如果提供则覆盖OpenAPI中的servers配置
    """
    
    # 读取OpenAPI文件
    with open(openapi_file_path, 'r', encoding='utf-8') as f:
        openapi_data = json.load(f)
    
    # 验证OpenAPI格式
    if not _validate_openapi_format(openapi_data):
        print("错误：无效的OpenAPI 3.0.3格式")
        return False
    
    # 创建Postman Collection结构
    postman_collection = _create_postman_collection(openapi_data)
    
    # 获取服务器信息
    if custom_base_url:
        base_url = custom_base_url
        print(f"使用自定义URL: {base_url}")
    else:
        servers = openapi_data.get("servers", [])
        base_url = servers[0].get("url", "") if servers else "http://localhost"
        print(f"使用OpenAPI中的URL: {base_url}")
    
    # 添加环境变量
    postman_collection["variable"] = _create_variables(base_url)
    
    # 处理路径
    paths = openapi_data.get("paths", {})
    
    # 按标签分组创建folders
    tags = openapi_data.get("tags", [])
    tag_folders = _create_tag_folders(tags)
    
    # 处理每个路径
    for path, path_data in paths.items():
        for method, method_data in path_data.items():
            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                _process_api_method(path, method, method_data, base_url, tag_folders)
    
    # 将有内容的folders添加到collection中
    for folder in tag_folders.values():
        if folder["item"]:  # 只添加有内容的folder
            postman_collection["item"].append(folder)
    
    # 写入输出文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(postman_collection, f, ensure_ascii=False, indent="\t")
    
    print(f"转换完成！输出文件: {output_file_path}")
    return True


def _validate_openapi_format(openapi_data):
    """验证OpenAPI格式"""
    if not openapi_data:
        return False
    
    # 检查必需字段
    required_fields = ['openapi', 'info', 'paths']
    for field in required_fields:
        if field not in openapi_data:
            print(f"错误：缺少必需字段 '{field}'")
            return False
    
    # 检查OpenAPI版本
    if openapi_data.get('openapi') != '3.0.3':
        print(f"警告：OpenAPI版本为 {openapi_data.get('openapi')}，预期为 3.0.3")
    
    return True


def _create_postman_collection(openapi_data):
    """创建Postman Collection基础结构"""
    info = openapi_data.get('info', {})
    
    return {
        "info": {
            "_postman_id": str(uuid.uuid4()),
            "name": info.get("title", "API Collection"),
            "description": info.get("description", ""),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "_exporter_id": "42962996"
        },
        "item": [],
        "variable": []
    }


def _create_variables(base_url):
    """创建环境变量"""
    parsed_url = urlparse(base_url)
    return [
        {
            "key": "baseUrl",
            "value": base_url,
            "type": "string"
        }
    ]


def _create_tag_folders(tags):
    """创建标签文件夹"""
    tag_folders = {}
    
    # 初始化标签文件夹
    for tag in tags:
        tag_name = tag.get("name", "未分类")
        tag_folders[tag_name] = {
            "name": tag_name,
            "item": []
        }
        # 如果有描述，添加到文件夹中
        if tag.get("description"):
            tag_folders[tag_name]["description"] = tag.get("description")
    
    return tag_folders


def _process_api_method(path, method, method_data, base_url, tag_folders):
    """处理单个API方法"""
    # 获取标签
    path_tags = method_data.get("tags", [])
    if not path_tags:
        path_tags = ["未分类"]
    
    # 创建请求项
    request_item = _create_request_item(path, method, method_data, base_url)
    
    # 添加到对应的标签文件夹
    for tag in path_tags:
        if tag in tag_folders:
            tag_folders[tag]["item"].append(request_item)
        else:
            # 如果标签不存在，创建新的标签文件夹
            tag_folders[tag] = {
                "name": tag,
                "item": [request_item]
            }


def _create_request_item(path, method, method_data, base_url):
    """创建单个请求项"""
    # 生成请求名称
    operation_id = method_data.get("operationId", "")
    summary = method_data.get("summary", "")
    request_name = operation_id or summary or f"{method.upper()} {path}"
    
    # 清理请求名称中的特殊字符
    request_name = re.sub(r'[^\w\s-]', '', request_name).strip()
    
    # 构建URL对象
    url_object = _create_url_object(path, base_url, method_data)
    
    # 处理请求头
    headers = _process_headers(method_data)
    
    # 处理请求体
    request_body = _process_request_body(method_data)
    
    # 处理响应示例
    response_examples = _process_response_examples(method_data.get('responses', {}))
    
    # 创建请求项
    request_item = {
        "name": request_name,
        "request": {
            "method": method.upper(),
            "header": headers,
            "url": url_object
        },
        "response": response_examples
    }
    
    # 只有在有请求体时才添加body字段
    if request_body:
        request_item["request"]["body"] = request_body
    
    # 添加协议配置文件行为
    if method.upper() in ['POST', 'PUT', 'PATCH']:
        request_item["protocolProfileBehavior"] = {
            "followAuthorizationHeader": True
        }
    
    return request_item


def _create_url_object(path, base_url, method_data):
    """创建符合Postman v2.1标准的URL对象"""
    # 构建完整URL用于raw字段
    if path.startswith('http'):
        full_url = path
    else:
        base = base_url.rstrip('/')
        if not path.startswith('/'):
            path = '/' + path
        full_url = base + path
    
    # 解析URL
    parsed = urlparse(full_url)
    
    # 分离协议和主机
    protocol = parsed.scheme or "https"
    host_parts = parsed.netloc.split('.') if parsed.netloc else []
    
    # 处理路径参数
    path_parts = []
    path_variables = []
    
    for part in parsed.path.split('/'):
        if part:
            # 检查是否是路径参数 {param}
            if part.startswith('{') and part.endswith('}'):
                param_name = part[1:-1]
                path_parts.append(f":{param_name}")
                path_variables.append({
                    "key": param_name,
                    "value": "",
                    "description": ""
                })
            else:
                path_parts.append(part)
    
    # 处理查询参数（从OpenAPI参数定义中获取）
    query_params = []
    parameters = method_data.get('parameters', [])
    for param in parameters:
        if param.get('in') == 'query':
            query_params.append({
                "key": param.get('name', ''),
                "value": param.get('example', ''),
                "description": param.get('description', ''),
                "disabled": not param.get('required', False)
            })
    
    # 如果URL中已有查询参数，也要包含
    if parsed.query:
        query_dict = parse_qs(parsed.query)
        for key, values in query_dict.items():
            # 避免重复添加
            if not any(q['key'] == key for q in query_params):
                query_params.append({
                    "key": key,
                    "value": values[0] if values else "",
                    "description": ""
                })
    
    url_object = {
        "raw": full_url,
        "protocol": protocol,
        "host": host_parts,
        "path": path_parts
    }
    
    # 只有在有查询参数时才添加query字段
    if query_params:
        url_object["query"] = query_params
    
    # 只有在有路径变量时才添加variable字段
    if path_variables:
        url_object["variable"] = path_variables
    
    return url_object


def _process_headers(method_data):
    """处理请求头"""
    headers = []
    
    # 处理OpenAPI中定义的header参数
    parameters = method_data.get('parameters', [])
    for param in parameters:
        if param.get('in') == 'header':
            headers.append({
                "key": param.get('name', ''),
                "value": param.get('example', ''),
                "description": param.get('description', ''),
                "type": "text"
            })
    
    return headers


def _process_request_body(method_data):
    """处理请求体"""
    request_body = method_data.get('requestBody')
    if not request_body:
        return None
    
    content = request_body.get('content', {})
    
    # 优先处理JSON格式
    if 'application/json' in content:
        json_schema = content['application/json'].get('schema', {})
        if json_schema:
            example_json = _generate_json_example(json_schema)
            return {
                "mode": "raw",
                "raw": json.dumps(example_json, ensure_ascii=False, indent=2),
                "options": {
                    "raw": {
                        "language": "json"
                    }
                }
            }
    
    # 处理表单数据
    elif 'application/x-www-form-urlencoded' in content:
        form_schema = content['application/x-www-form-urlencoded'].get('schema', {})
        if form_schema:
            form_data = []
            properties = form_schema.get('properties', {})
            for key, prop in properties.items():
                form_data.append({
                    "key": key,
                    "value": prop.get('example', ''),
                    "description": prop.get('description', ''),
                    "type": "text"
                })
            return {
                "mode": "urlencoded",
                "urlencoded": form_data
            }
    
    # 处理multipart/form-data
    elif 'multipart/form-data' in content:
        form_schema = content['multipart/form-data'].get('schema', {})
        if form_schema:
            form_data = []
            properties = form_schema.get('properties', {})
            for key, prop in properties.items():
                form_data.append({
                    "key": key,
                    "value": prop.get('example', ''),
                    "description": prop.get('description', ''),
                    "type": "text"
                })
            return {
                "mode": "formdata",
                "formdata": form_data
            }
    
    # 处理纯文本
    elif 'text/plain' in content:
        return {
            "mode": "raw",
            "raw": "example text",
            "options": {
                "raw": {
                    "language": "text"
                }
            }
        }
    
    return None


def _generate_json_example(schema):
    """根据JSON Schema生成示例数据"""
    if not schema:
        return {}
    
    example = {}
    properties = schema.get('properties', {})
    
    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get('type', 'string')
        
        if prop_type == 'string':
            example[prop_name] = prop_schema.get('example', f"example_{prop_name}")
        elif prop_type == 'number':
            example[prop_name] = prop_schema.get('example', 0)
        elif prop_type == 'integer':
            example[prop_name] = prop_schema.get('example', 0)
        elif prop_type == 'boolean':
            example[prop_name] = prop_schema.get('example', False)
        elif prop_type == 'array':
            items_schema = prop_schema.get('items', {})
            example[prop_name] = [_generate_json_example(items_schema)]
        elif prop_type == 'object':
            example[prop_name] = _generate_json_example(prop_schema)
        else:
            example[prop_name] = prop_schema.get('example', '')
    
    return example


def _process_response_examples(responses):
    """处理响应示例"""
    response_examples = []
    
    for status_code, response_data in responses.items():
        # 只处理数字状态码
        if not status_code.isdigit():
            continue
        
        description = response_data.get('description', '')
        content = response_data.get('content', {})
        
        # 处理不同的内容类型
        for content_type, content_data in content.items():
            schema = content_data.get('schema', {})
            example = content_data.get('example')
            
            # 生成响应体
            if example is not None:
                if content_type == 'application/json':
                    body = json.dumps(example, ensure_ascii=False, indent=2)
                else:
                    body = str(example)
            elif schema:
                if content_type == 'application/json':
                    example_data = _generate_json_example(schema)
                    body = json.dumps(example_data, ensure_ascii=False, indent=2)
                else:
                    body = "example response"
            else:
                body = ""
            
            # 确定预览语言
            preview_language = "json" if content_type == 'application/json' else "text"
            
            response_examples.append({
                "name": f"{status_code} {description}" if description else f"{status_code} Response",
                "originalRequest": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "",
                        "host": [],
                        "path": []
                    }
                },
                "status": description or f"Status {status_code}",
                "code": int(status_code),
                "_postman_previewlanguage": preview_language,
                "header": [
                    {
                        "key": "Content-Type",
                        "value": content_type
                    }
                ],
                "cookie": [],
                "body": body
            })
            
            # 只处理第一个内容类型
            break
    
    return response_examples


def main():
    """主函数"""
    import sys
    
    # 处理命令行参数
    custom_base_url = "Input_Base_Url"  # 自定义基础URL，如果提供则覆盖OpenAPI中的servers配置
    if len(sys.argv) > 1:
        openapi_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "converted_postman_collection.json"
        custom_base_url = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        # 默认文件路径
        openapi_file = "RAP-PAS V2-1094-OPENAPI3-20250723174017.json"   # 待转换格式的文件名（需与脚本放在同一目录下）
        output_file = "Revamp_PAS_API_v2.1.postman_collection.json"    # 转换格式输出的文件名
    
    try:
        # 检查输入文件是否存在
        if not os.path.exists(openapi_file):
            print(f"错误：找不到输入文件 {openapi_file}")
            print("用法: python convert_openapi_to_postman.py <openapi_file> [output_file]")
            sys.exit(1)
        
        print(f"开始转换: {openapi_file} -> {output_file}")
        
        # 执行转换
        success = convert_openapi_to_postman(openapi_file, output_file, custom_base_url)
        
        if success:
            print("\n✅ 转换成功完成！")
            print(f"📁 输出文件: {output_file}")
            print("\n💡 提示: 您可以将生成的文件导入到Postman中使用")
            print("\n📖 使用方法:")
            print("1. 打开 Postman")
            print("2. 点击 Import")
            print(f"3. 选择生成的文件: {output_file}")
            print("\n📋 命令行参数说明:")
            print("python convert_openapi_to_postman.py <openapi_file> [output_file] [custom_base_url]")
            print("- openapi_file: OpenAPI JSON文件路径")
            print("- output_file: 输出的Postman Collection文件路径（可选）")
            print("- custom_base_url: 自定义基础URL（可选，覆盖OpenAPI中的servers配置）")
        else:
            print("❌ 转换失败！")
            sys.exit(1)
            
    except FileNotFoundError:
        print(f"❌ 错误：找不到文件 {openapi_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ 错误：JSON格式无效 - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误：转换过程中发生异常 - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
