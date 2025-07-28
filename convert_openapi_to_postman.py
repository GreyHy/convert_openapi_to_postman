# @Time:2025/7/24
# @Author:yong.huang@shopee.com

"""
OpenAPI 3.0.3 到 Postman Collection v2.1 转换器
"""

import json
import uuid
import re
from datetime import datetime

def convert_openapi_to_postman(openapi_file_path, output_file_path):
    """
    将OpenAPI 3.0.3文件转换为Postman Collection v2.1格式
    """
    
    # 读取OpenAPI文件
    with open(openapi_file_path, 'r', encoding='utf-8') as f:
        openapi_data = json.load(f)
    
    # 创建Postman Collection结构
    postman_collection = {
        "info": {
            "_postman_id": str(uuid.uuid4()),
            "name": openapi_data.get("info", {}).get("title", "API Collection"),
            "description": openapi_data.get("info", {}).get("description", ""),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "_exporter_id": "42962996"
        },
        "item": []
    }
    
    # 获取服务器信息
    servers = openapi_data.get("servers", [])
    base_url = servers[0].get("url", "") if servers else ""
    
    # 处理路径
    paths = openapi_data.get("paths", {})
    
    # 按标签分组
    tags = openapi_data.get("tags", [])
    tag_groups = {}
    
    # 初始化标签组
    for tag in tags:
        tag_name = tag.get("name", "未分类")
        tag_groups[tag_name] = {
            "name": tag_name,
            "description": tag.get("description", ""),
            "item": []
        }
    
    # 处理每个路径
    for path, path_data in paths.items():
        for method, method_data in path_data.items():
            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                
                # 获取标签
                path_tags = method_data.get("tags", [])
                if not path_tags:
                    path_tags = ["未分类"]
                
                # 创建请求项
                request_item = create_request_item(path, method, method_data, base_url)
                
                # 添加到对应的标签组
                for tag in path_tags:
                    if tag in tag_groups:
                        tag_groups[tag]["item"].append(request_item)
                    else:
                        # 如果标签不存在，创建新的标签组
                        tag_groups[tag] = {
                            "name": tag,
                            "description": "",
                            "item": [request_item]
                        }
    
    # 将标签组添加到collection中
    for tag_group in tag_groups.values():
        if tag_group["item"]:  # 只添加有内容的标签组
            postman_collection["item"].append(tag_group)
    
    # 写入输出文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(postman_collection, f, ensure_ascii=False, indent=2)
    
    print(f"转换完成！输出文件: {output_file_path}")

def create_request_item(path, method, method_data, base_url):
    """
    创建单个请求项
    """
    
    # 生成请求名称
    operation_id = method_data.get("operationId", "")
    summary = method_data.get("summary", "")
    request_name = operation_id or summary or f"{method.upper()} {path}"
    
    # 构建完整URL
    full_url = base_url + path if base_url else path
    
    # 处理路径参数
    url_parts = parse_url(full_url)
    
    # 处理查询参数
    query_params = []
    if "parameters" in method_data:
        for param in method_data["parameters"]:
            if param.get("in") == "query":
                query_params.append({
                    "key": param.get("name", ""),
                    "value": "",
                    "description": param.get("description", ""),
                    "disabled": True
                })
    
    # 处理请求体
    body = None
    if method.upper() in ['POST', 'PUT', 'PATCH'] and "requestBody" in method_data:
        body = create_request_body(method_data["requestBody"])
    
    # 创建请求项
    request_item = {
        "name": request_name,
        "request": {
            "method": method.upper(),
            "header": [],
            "url": url_parts,
            "description": method_data.get("description", "")
        }
    }
    
    # 添加查询参数
    if query_params:
        request_item["request"]["url"]["query"] = query_params
    
    # 添加请求体
    if body:
        request_item["request"]["body"] = body
    
    # 添加响应示例
    responses = []
    if "responses" in method_data:
        responses = create_response_examples(method_data["responses"])
    
    if responses:
        request_item["response"] = responses
    
    return request_item

def parse_url(url):
    """
    解析URL并提取路径参数
    """
    # 分离协议、主机和路径
    if url.startswith("http"):
        # 完整URL
        match = re.match(r"(https?://[^/]+)(.*)", url)
        if match:
            base_url = match.group(1)
            path = match.group(2)
        else:
            base_url = ""
            path = url
    else:
        # 相对路径
        base_url = ""
        path = url
    
    # 解析主机部分
    if base_url:
        protocol_host = base_url.split("://")
        if len(protocol_host) == 2:
            protocol = protocol_host[0]
            host = protocol_host[1].split("/")[0]
        else:
            protocol = "https"
            host = base_url
    else:
        protocol = "https"
        host = "api.example.com"
    
    # 解析路径
    path_parts = path.split("/")
    path_variables = []
    
    # 处理路径参数
    for i, part in enumerate(path_parts):
        if part.startswith("{") and part.endswith("}"):
            param_name = part[1:-1]
            path_parts[i] = f":{param_name}"
            path_variables.append({
                "key": param_name,
                "value": "",
                "description": f"Path parameter: {param_name}"
            })
    
    return {
        "raw": url,
        "protocol": protocol,
        "host": host.split("."),
        "path": [p for p in path_parts if p],
        "variable": path_variables
    }

def create_request_body(request_body):
    """
    创建请求体
    """
    content = request_body.get("content", {})
    
    # 优先使用application/json
    if "application/json" in content:
        schema = content["application/json"].get("schema", {})
        example = content["application/json"].get("example", {})
        
        return {
            "mode": "raw",
            "raw": json.dumps(example, ensure_ascii=False, indent=2) if example else "{}",
            "options": {
                "raw": {
                    "language": "json"
                }
            }
        }
    
    # 如果没有JSON，尝试其他格式
    for content_type in content:
        return {
            "mode": "raw",
            "raw": "",
            "options": {
                "raw": {
                    "language": "text"
                }
            }
        }
    
    return None

def create_response_examples(responses):
    """
    创建响应示例
    """
    examples = []
    
    for status_code, response_data in responses.items():
        if status_code == "default":
            continue
            
        # 创建响应示例
        example = {
            "name": f"{status_code} {response_data.get('description', 'Response')}",
            "originalRequest": {
                "method": "GET",
                "header": [],
                "url": {
                    "raw": "https://api.example.com/path",
                    "protocol": "https",
                    "host": ["api", "example", "com"],
                    "path": ["path"]
                }
            },
            "status": response_data.get("description", "OK"),
            "code": int(status_code) if status_code.isdigit() else 200,
            "_postman_previewlanguage": "json",
            "header": [
                {
                    "key": "content-type",
                    "value": "application/json; charset=utf-8"
                }
            ],
            "cookie": [],
            "body": "{}"
        }
        
        # 如果有响应内容，添加到body中
        if "content" in response_data:
            content = response_data["content"]
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                example_body = content["application/json"].get("example", {})
                example["body"] = json.dumps(example_body, ensure_ascii=False, indent=2)
        
        examples.append(example)
    
    return examples

if __name__ == "__main__":
    # 转换文件
    input_file = "RAP-PAS V2-1094-OPENAPI3-20250723174017.json"  # 待转换格式的文件名（需与脚本放在同一目录下）
    output_file = "PAS_Postman_Collection_v2.1.json" # 转换格式输出的文件名 
    
    try:
        convert_openapi_to_postman(input_file, output_file)
        print("转换成功！")
    except Exception as e:
        print(f"转换失败: {e}") 