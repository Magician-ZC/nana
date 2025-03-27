class Config:
    ''' LLM配置 '''
    LLM_API_URL = "https://api.ppinfra.com/v3/openai"
    LLM_API_KEY = "sk_8wpzHpLKzD8JzBHfTblPzLNK54PmH2Tk7VRJmHFZ2g8"
    
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
    ENABLE_TTS = False  # 默认不启用普通TTS功能
    ENABLE_SUPER_TTS = False  # 默认不启用超拟人TTS功能
    
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
    TTS_AUE = "lame"  # 音频编码，可选值：raw(未压缩)、lame(mp3)、speex(speex格式压缩)、speex-wb(speex格式压缩)
    TTS_AUF = "audio/L16;rate=16000"  # 音频采样率，可选值：audio/L16;rate=8000、audio/L16;rate=16000
    TTS_VCN = "xiaoyan"  # 发音人，可选值：详见科大讯飞文档中的发音人列表
    TTS_TTE = "utf8"  # 文本编码格式，可选值：GB2312、GBK、BIG5、UNICODE、GB18030、UTF8
    TTS_TEXT_LENGTH_LIMIT = 2000  # 单次合成文本长度限制（汉字）
    
    # TTS高级参数
    TTS_SPEED = 50  # 语速，取值范围：[0,100]，默认为50
    TTS_VOLUME = 50  # 音量，取值范围：[0,100]，默认为50
    TTS_PITCH = 50  # 音高，取值范围：[0,100]，默认为50
    
    # 超拟人TTS配置
    SUPER_TTS_URL = "wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/mcd9m97e6"  # 超拟人TTS服务地址
    SUPER_TTS_VCN = "x4_lingfeiyi_oral"  # 超拟人TTS发音人, x4_lingfeiyi_oral、x4_lingfeier_oral、x4_linglinghan_oral等
    SUPER_TTS_ORAL_LEVEL = "mid"  # 口语化程度，high、mid、low
    
    # 超拟人TTS高级参数
    SUPER_TTS_SPARK_ASSIST = 1  # 是否通过大模型进行口语化，1开启，0关闭
    SUPER_TTS_STOP_SPLIT = 0  # 是否关闭服务端拆句，1关闭，0不关闭  
    SUPER_TTS_REMAIN = 0  # 是否保留原书面语，1保留，0不保留
    
    ''' 对话历史配置 '''
    MAX_TURNS = 20  # 最多保存20轮对话，超过后自动归档一半
    
    @classmethod
    def is_tts_enabled(cls) -> bool:
        """判断是否启用普通TTS功能"""
        return cls.ENABLE_TTS and cls.XFYUN_APP_ID and cls.XFYUN_API_KEY and cls.XFYUN_API_SECRET
        
    @classmethod
    def is_super_tts_enabled(cls) -> bool:
        """判断是否启用超拟人TTS功能"""
        return cls.ENABLE_SUPER_TTS and cls.XFYUN_APP_ID and cls.XFYUN_API_KEY and cls.XFYUN_API_SECRET
