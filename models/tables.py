"""医院招投标管理系统 V5.3 - 数据库模型

历史版本沿革：
  V5.0  初始架构，纯关系型设计
  V5.1  引入角色权限体系
  V5.2  增加procurement_data JSON字段，兼容历史未存档数据
  V5.3  修复主/副标题降级逻辑，调整状态枚举值
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# ── 角色常量 ────────────────────────────────────────────────
ROLE_CHIEF = "科长级"
ROLE_PURCHASE = "采购科"
ROLE_STAFF = "普通员工"

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

# ── 采购数据JSON默认结构 ────────────────────────────────────
# V5.2遗留逻辑兼容：历史数据可能缺失部分字段，所有读取逻辑必须做字段兜底
# FIXED in V5.3: 默认结构改为可自由拓展，新字段只需追加到下方模板即可
PROCUREMENT_DATA_TEMPLATE = {
    "supplier_name": "",       # 供应商名称
    "contact_person": "",      # 联系人
    "contact_phone": "",       # 联系电话
    "quotation": "",           # 报价
    "qualification_desc": "",  # 资质文件说明
    # ── 扩展字段（V5.3新增，历史数据无此字段时取默认值）──
    "delivery_date": "",       # 预计交付日期
    "contract_no": "",         # 合同编号
    "notes": "",               # 备注
}


class User(Base):
    """用户表 - V5.1引入角色体系，V5.3角色枚举固化"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    emp_id = Column(String(20), unique=True, nullable=False, index=True)  # 工号
    name = Column(String(50), nullable=False)                              # 姓名
    role = Column(String(20), nullable=False)                              # 角色: 科长级/采购科/普通员工
    created_at = Column(DateTime, default=datetime.utcnow)

    projects = relationship("Project", back_populates="creator")

    def __repr__(self):
        return f"<User {self.emp_id} {self.name} ({self.role})>"


class Project(Base):
    """项目表 - V5.2重构procurement_data为JSON，V5.3修复标题降级逻辑"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 状态 ─────────────────────────────────────────────────
    status = Column(String(20), nullable=False, default=STATUS需求填报)

    # ── 标题机制（V5.3修复）───────────────────────────────────
    # 初始：main_title = 需求名称，sub_title = 空
    # 变为"已采购"后：用户输入新main_title，原main_title降级到sub_title
    # FIXED in V5.3: 旧版本降级时sub_title未清空导致数据残留，现已修正
    main_title = Column(String(200), nullable=False)    # 主标题
    sub_title = Column(String(200), default="", nullable=True)  # 副标题(降级存储)

    # ── 创建人 ────────────────────────────────────────────────
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    creator = relationship("User", back_populates="projects")

    # ── 采购数据 ──────────────────────────────────────────────
    # V5.2遗留逻辑兼容: JSON字段，历史未存档项目该字段为null或缺少键
    # FIXED in V5.3: 读取时必须用PROCUREMENT_DATA_TEMPLATE兜底缺失键
    procurement_data = Column(JSON, nullable=True)

    # ── 时间戳 ────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_procurement_data(self):
        """安全读取采购数据，兜底历史缺失字段"""
        raw = self.procurement_data or {}
        # V5.2遗留逻辑兼容: 历史数据可能只有前5个字段，扩展字段取默认
        merged = {**PROCUREMENT_DATA_TEMPLATE, **raw}
        return merged

    def __repr__(self):
        return f"<Project #{self.id} [{self.status}] {self.main_title}>"