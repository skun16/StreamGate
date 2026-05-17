from enum import Enum

from fastapi import Request, HTTPException


class UserGroup(str, Enum):
    """
    用户分组。
    """

    OFFICE_LEADER = "office_leader"
    DEPARTMENT_LEADER = "department_leader"


# 开发阶段临时用户映射表
# 后面可以替换成数据库、JWT、统一身份认证、OA 用户体系等。
USER_GROUP_MAP: dict[str, UserGroup] = {
    "office_test": UserGroup.OFFICE_LEADER,
    "department_test": UserGroup.DEPARTMENT_LEADER,
}


def get_user_group_from_request(request: Request) -> UserGroup:
    """
    从请求中识别用户分组。

    当前开发阶段：
    - 从请求头 X-User-Id 读取用户 ID
    - 根据 USER_GROUP_MAP 映射到用户分组

    示例：
    X-User-Id: office_test       -> office_leader
    X-User-Id: department_test   -> department_leader
    """

    user_id = request.headers.get("X-User-Id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="缺少请求头 X-User-Id，无法识别用户身份",
        )

    user_group = USER_GROUP_MAP.get(user_id)

    if not user_group:
        raise HTTPException(
            status_code=403,
            detail=f"用户 {user_id} 没有可用的 StreamGate 权限",
        )

    return user_group