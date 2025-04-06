import os

class Config:
    ''' LLM配置 '''

    LLM_API_URL = os.environ.get("LLM_API_URL", "https://api.ppinfra.com/v3/openai")
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "sk_8wpzHpLKzD8JzBHfTblPzLNK54PmH2Tk7VRJmHFZ2g8")
    
    ''' 向量模型配置 '''
    EMBEDDING_API_KEY = "sk-eziehqfupwjhffcnixziqozcqxaqkgnzshgvueemosdijebj"
    EMBEDDING_API_URL = "https://api.siliconflow.cn/v1/embeddings"
    EMBEDDING_MODEL = "BAAI/bge-m3"
    EMBEDDING_DIMENSION = 768
    
    ''' 科大讯飞语音识别配置 '''
    XFYUN_APP_ID = "890910a0"  # 填入你的APP_ID
    XFYUN_API_KEY = "b2bdf08862cf3ac0e5cbdc81a8066456"  # 填入你的API_KEY
    XFYUN_API_SECRET = "NTMyZDI1OWQzNWI4ZDcwODYzYzA0YzIz"  # 填入你的API_SECRET
    
    ''' 
        TTS服务配置（科大讯飞）
    '''
    # TTS功能配置
    ENABLE_TTS = False  # 是否启用普通TTS
    ENABLE_SUPER_TTS = True  # 是否启用超拟人TTS
    
    # 普通TTS可用音色列表
    TTS_VOICE_LIST = [
        {"name": "小燕", "value": "xiaoyan"},
        {"name": "许久", "value": "aisjiuxu"},
        {"name": "小萍", "value": "aisxping"},
        {"name": "小婧", "value": "aisjinger"},
        {"name": "许小宝", "value": "aisbabyxu"},
    ]
    
    # 超拟人TTS可用音色列表
    SUPER_TTS_VOICE_LIST = [
        {"name": "聆飞逸", "value": "x4_lingfeiyi_oral"},
        {"name": "聆小璇", "value": "x4_lingxiaoxuan_oral"},
        {"name": "聆玉言", "value": "x4_lingyuyan_oral"},
    ]
    
    # 普通TTS音频格式配置
    TTS_AUE = "lame"  # 音频编码，可选值：raw（未压缩的pcm），lame（mp3格式）
    TTS_AUF = "audio/L16;rate=16000"  # 音频采样率，可选值：audio/L16;rate=8000，audio/L16;rate=16000
    TTS_VCN = "xiaoyan"  # 发音人，可选值：xiaoyan, aisjiuxu等
    TTS_TTE = "utf8"  # 文本编码
    TTS_TEXT_LENGTH_LIMIT = 100  # 文本长度限制，降低以减少API错误
    
    # TTS高级参数
    TTS_SPEED = 70  # 语速，可选值：[0-100]，默认50
    TTS_VOLUME = 50  # 音量，可选值：[0-100]，默认50
    TTS_PITCH = 50  # 音高，可选值：[0-100]，默认50
    
    # 超拟人TTS配置
    SUPER_TTS_URL = "wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/mcd9m97e6"  # 超拟人TTS服务地址
    SUPER_TTS_VCN = "x4_lingxiaoxuan_oral"  # 超拟人发音人
    SUPER_TTS_ORAL_LEVEL = "mid"  # 口语化程度，high、mid、low
    
    # 超拟人TTS高级参数
    SUPER_TTS_SPARK_ASSIST = 1  # 是否通过大模型进行口语化，1开启，0关闭
    SUPER_TTS_STOP_SPLIT = 0  # 是否关闭服务端拆句，1关闭，0不关闭  
    SUPER_TTS_REMAIN = 0  # 是否保留原书面语，1保留，0不保留
    SUPER_TTS_TEXT_LENGTH_LIMIT = 80  # 超拟人TTS文本长度限制，降低以减少API错误
    
    # 新增：聊天效果配置
    TYPING_SPEED = 155  # 打字速度，值越小速度越快，单位是毫秒/字符，默认38毫秒（约26字/秒）
    
    ''' 对话历史配置 '''
    MAX_TURNS = 20  # 最多保存20轮对话，超过后自动归档一半
    
    # 添加视觉模型配置
    VISION_MODEL_ENABLED = os.environ.get("VISION_MODEL_ENABLED", "false").lower() == "true"
    VISION_MODEL_API_KEY = os.environ.get("VISION_MODEL_API_KEY", LLM_API_KEY)
    VISION_MODEL_API_URL = os.environ.get("VISION_MODEL_API_URL", "https://api.openai.com/v1")
    
    @classmethod
    def is_tts_enabled(cls) -> bool:
        """判断是否启用普通TTS功能"""
        return cls.ENABLE_TTS and cls.XFYUN_APP_ID and cls.XFYUN_API_KEY and cls.XFYUN_API_SECRET
        
    @classmethod
    def is_super_tts_enabled(cls) -> bool:
        """判断是否启用超拟人TTS功能"""
        return cls.ENABLE_SUPER_TTS and cls.XFYUN_APP_ID and cls.XFYUN_API_KEY and cls.XFYUN_API_SECRET
