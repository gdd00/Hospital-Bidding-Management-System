"""医院招投标管理系统 V5.3 - 数据库模型

历史版本沿革：
  V5.0  初始架构，纯关系型设计
  V5.1  引入角色权限体系
  V5.2  增加procurement_data JSON字段，兼容历史未存档数据
  V5.3  修复主/副标题降级逻辑，调整状态枚举值
        重构权限体系：角色→分组，User增加密码+外键关联Group
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# ── 项目状态常量 ────────────────────────────────────────────
STATUS需求填报 = "需求填报"
STATUS寻找供应商 = "寻找供应商"
STATUS已采购 = "已采购"
STATUS计划报废 = "计划报废"
STATUS已报废 = "已报废"

ALL_STATUSES = [
    STATUS需求填报,
    STATUS寻找供应商,
    STATUS已采购,
    STATUS计划报废,
    STATUS已报废,
]

# ── 采购数据JSON模板 ──────────────────────────────────────────
# V5.3重构: procurement_data从单个对象改为数组，每条记录代表一个供应商
# 每次补充采购数据追加一条，而非覆盖旧记录
PROCUREMENT_DATA_TEMPLATE = {
    "supplier_name": "",       # 供应商名称
    "contact_person": "",      # 联系人
    "contact_phone": "",       # 联系电话
    "quotation": "",           # 报价
    "qualification_desc": "",  # 资质文件说明
    "delivery_date": "",       # 预计交付日期
    "contract_no": "",         # 合同编号
    "notes": "",               # 备注
}

# ── 权限Key常量 ──────────────────────────────────────────────
# FIXED in V5.3: 权限从硬编码角色字符串改为可配置的permission key
# 分组的permissions JSON存储这些key的列表
PERM_CREATE_PROJECT = "create_project"
PERM_WRITE_PROCUREMENT = "write_procurement"
PERM_ADVANCE_STATUS = "advance_status"
PERM_ADVANCE_TO_SUPPLIER = "advance_to_supplier"
PERM_VIEW_DASHBOARD = "view_dashboard"
PERM_MANAGE_ACCOUNTS = "manage_accounts"

ALL_PERMS = [
    PERM_CREATE_PROJECT,
    PERM_WRITE_PROCUREMENT,
    PERM_ADVANCE_STATUS,
    PERM_ADVANCE_TO_SUPPLIER,
    PERM_VIEW_DASHBOARD,
    PERM_MANAGE_ACCOUNTS,
]

# ── 默认分组模板 ──────────────────────────────────────────────
# V5.2遗留逻辑兼容: 旧版角色"科长级/采购科/普通员工"映射为以下分组
DEFAULT_GROUPS = {
    "科长组": {
        "permissions": [
            PERM_CREATE_PROJECT,
            PERM_ADVANCE_STATUS,
            PERM_ADVANCE_TO_SUPPLIER,
            PERM_VIEW_DASHBOARD,
            PERM_MANAGE_ACCOUNTS,
        ],
    },
    "采购组": {
        "permissions": [
            PERM_WRITE_PROCUREMENT,
            PERM_ADVANCE_TO_SUPPLIER,
        ],
    },
    "员工组": {
        "permissions": [],  # 普通员工: 仅可查看列表，无操作权限
    },
}


class Group(Base):
    """权限分组表 - V5.3新增，替代旧版硬编码角色字符串
    permissions字段用JSON存储权限key列表，可动态拓展"""
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)          # 分组名称
    permissions = Column(JSON, nullable=False, default=list)         # 权限key列表
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="group")

    def has_perm(self, perm_key: str) -> bool:
        """检查分组是否拥有某权限"""
        perms = self.permissions or []
        return perm_key in perms

    def __repr__(self):
        return f"<Group {self.name} perms={self.permissions}>"


class User(Base):
    """用户表 - V5.3重构: 增加密码+分组外键，移除旧版role字段
    V5.2遗留逻辑兼容: role字段已移除，但init_db迁移脚本会自动映射"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    emp_id = Column(String(20), unique=True, nullable=False, index=True)  # 工号
    name = Column(String(50), nullable=False)                              # 姓名
    password_hash = Column(String(128), nullable=False)                    # 密码哈希
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)    # 所属分组
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("Group", back_populates="users")
    projects = relationship("Project", back_populates="creator")

    def has_perm(self, perm_key: str) -> bool:
        """通过所属分组检查权限"""
        return self.group.has_perm(perm_key) if self.group else False

    def __repr__(self):
        gname = self.group.name if self.group else "?"
        return f"<User {self.emp_id} {self.name} ({gname})>"


class Project(Base):
    """项目表 - V5.3: procurement_data改为数组(多条供应商记录)"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 状态 ─────────────────────────────────────────────────
    status = Column(String(20), nullable=False, default=STATUS需求填报)

    # ── 标题机制（V5.3修复）───────────────────────────────────
    main_title = Column(String(200), nullable=False)
    sub_title = Column(String(200), default="", nullable=True)

    # ── 创建人 ────────────────────────────────────────────────
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    creator = relationship("User", back_populates="projects")

    # ── 采购数据(数组) ────────────────────────────────────────
    # V5.3重构: 从单个JSON对象改为JSON数组，每条是一条供应商记录
    # V5.2遗留逻辑兼容: 旧数据可能是单个对象，get_procurement_list()会自动转换
    procurement_data = Column(JSON, nullable=True)

    # ── 时间戳 ────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_procurement_list(self):
        """安全读取采购数据列表，兼容V5.2旧格式(单个对象)"""
        raw = self.procurement_data
        if raw is None:
            return []
        # V5.2遗留逻辑兼容: 旧版procurement_data是单个dict而非list
        if isinstance(raw, dict):
            return [raw]
        return raw

    def has_procurement_records(self) -> bool:
        """是否已有至少一条采购记录"""
        return len(self.get_procurement_list()) > 0

    def __repr__(self):
        return f"<Project #{self.id} [{self.status}] {self.main_title}>"