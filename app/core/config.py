from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    StreamGate 项目配置。

    负责从 .env 文件中读取：
    1. RAGFlow 基础地址
    2. RAGFlow API Key
    3. 不同用户分组、不同功能类型对应的 Chat ID
    4. HTTP 超时和连接池参数
    5. 并发控制参数
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用名称
    APP_NAME: str = "StreamGate"

    # RAGFlow 基础地址，例如：http://192.168.111.200
    RAGFLOW_BASE_URL: str

    # RAGFlow API Key
    RAGFLOW_API_KEY: str

    # 处室领导：知识库问答 Chat ID
    RAGFLOW_OFFICE_LEADER_KB_CHAT_ID: str

    # 处室领导：文件总结 Chat ID
    RAGFLOW_OFFICE_LEADER_SUMMARY_CHAT_ID: str

    # 厅领导：知识库问答 Chat ID
    RAGFLOW_DEPARTMENT_LEADER_KB_CHAT_ID: str

    # 厅领导：文件总结 Chat ID
    RAGFLOW_DEPARTMENT_LEADER_SUMMARY_CHAT_ID: str

    # RAGFlow HTTP 超时配置
    RAGFLOW_CONNECT_TIMEOUT: float = 10.0
    RAGFLOW_READ_TIMEOUT: float = 180.0
    RAGFLOW_WRITE_TIMEOUT: float = 10.0
    RAGFLOW_POOL_TIMEOUT: float = 10.0

    # HTTP 连接池配置
    HTTP_MAX_CONNECTIONS: int = 200
    HTTP_MAX_KEEPALIVE_CONNECTIONS: int = 50

    # 并发控制
    GLOBAL_CONCURRENCY: int = 100
    RAGFLOW_CONCURRENCY: int = 30


settings = Settings()