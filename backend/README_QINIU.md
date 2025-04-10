# 七牛云视频上传功能

本模块实现了视频上传到七牛云的功能，包括获取上传配置、计算七牛云eTag、上传文件和通知服务端上传结果。

## 功能概述

1. 通过API获取七牛云上传配置
2. 将视频文件缓存到本地临时目录
3. 计算视频文件的七牛云eTag
4. 使用七牛云SDK上传视频文件
5. 通知服务端上传结果

## API使用

### 视频上传接口

```
POST /api/upload-video
```

**请求参数:**

- `file`: 要上传的视频文件 (表单文件)
- `file_type`: 文件类型，默认为"avi"

**请求头:**

- `Authorization`: Bearer token，例如：`Bearer 0035f0043dac4be4ba8db607b1c948c5`

**响应示例:**

```json
{
  "success": true,
  "message": "视频上传成功",
  "data": {
    "etag": "Fi4EQpFa5HYOzUULxuInh0GN_P80",
    "url": "http://example.domain.com/Fi4EQpFa5HYOzUULxuInh0GN_P80",
    "upload_result": {
      "status": 1,
      "etag": "Fi4EQpFa5HYOzUULxuInh0GN_P80",
      "local_path": "/path/to/temp/video.avi",
      "remote_path": "http://example.domain.com/Fi4EQpFa5HYOzUULxuInh0GN_P80"
    },
    "notify_result": {
      "code": 200,
      "message": "上传成功"
    }
  }
}
```

## 测试方法

可以使用提供的测试脚本进行测试，有三种测试方式：

### 1. 仅测试获取七牛云配置

```bash
python test_qiniu_upload.py config 0035f0043dac4be4ba8db607b1c948c5
```

### 2. 使用本地API上传视频（推荐）

```bash
python test_qiniu_upload.py /path/to/video.avi 0035f0043dac4be4ba8db607b1c948c5 --file-type avi
```

### 3. 直接使用七牛SDK上传（不经过本地API）

```bash
python test_qiniu_upload.py /path/to/video.avi 0035f0043dac4be4ba8db607b1c948c5 --file-type avi --direct
```

## 实现流程

1. 发送请求到 `http://192.168.3.210:30080/app-api/system/family-and-manage/oss/common/get-oss-upload-info` 获取上传配置
2. 将视频缓存到本地临时目录
3. 使用特定算法计算eTag
4. 利用七牛云SDK上传文件
5. 发送请求到 `http://192.168.3.210:30080/app-api/equipment/emotion/video-upload-back` 通知上传结果

## 依赖

- qiniu>=7.10.0：七牛云SDK
- requests：HTTP请求
- fastapi：Web API框架

## 注意事项

- 临时文件存储在 `backend/temp_uploads` 目录中
- 请确保服务器有足够的磁盘空间用于存储临时视频文件
- 上传大文件时可能需要更长的处理时间 