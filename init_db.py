"""医院招投标管理系统 V5.3 - 数据库初始化与测试数据生成

执行方式: python init_db.py
效果: 建表 + 插入3个测试用户 + 插入5条不同状态的项目

V5.2遗留逻辑兼容: 历史procurement_data字段为null的记录仍可被安全读取
FIXED in V5.3: 初始化脚本不再硬编码SQL，改用ORM插入
"""

import sys
import os

# 确保可以 import models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.tables import (
    Base, User, Project,
    ROLE_CHIEF, ROLE_PURCHASE, ROLE_STAFF,
    PROCUREMENT_DATA_TEMPLATE,
    STATUS需求填报, STATUS寻找供应商, STATUS已采购,
    STATUS计划报废, STATUS已报废,
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hospital.db")
ENGINE_URL = f"sqlite:///{DB_PATH}"


def create_engine_and_session():
    engine = create_engine(ENGINE_URL, echo=False)
    Base.metadata.create_all(engine)
    # FIXED in V5.3: 旧版用connect()手动commit，现改用session保证事务一致性
    Session = sessionmaker(bind=engine)
    return engine, Session()


def seed_users(session):
    """插入3个测试用户"""
    users = [
        User(emp_id="EMP001", name="科长A", role=ROLE_CHIEF),
        User(emp_id="EMP002", name="采购牛马B", role=ROLE_PURCHASE),
        User(emp_id="EMP003", name="员工C", role=ROLE_STAFF),
    ]
    session.add_all(users)
    session.flush()  # 确保.id可用
    return users


def seed_projects(session, chief, purchaser, staff):
    """插入5条覆盖全部状态的测试项目"""

    # 1) 需求填报 — 刚创建，采购数据为空
    p1 = Project(
        main_title="ICU监护仪需求申报",
        sub_title="",
        status=STATUS需求填报,
        creator_id=chief.id,
        procurement_data=None,  # V5.2遗留逻辑兼容: null代表尚未进入采购阶段
    )

    # 2) 寻找供应商 — 采购数据部分填写
    p2 = Project(
        main_title="手术室LED无影灯采购",
        sub_title="",
        status=STATUS寻找供应商,
        creator_id=chief.id,
        procurement_data={
            "supplier_name": "明视医疗设备公司",
            "contact_person": "张经理",
            "contact_phone": "138-0000-1234",
            "quotation": "¥85,000/台",
            "qualification_desc": "三类医疗器械许可证",
            # 扩展字段暂未填写 — 读取时由TEMPLATE兜底
        },
    )

    # 3) 已采购 — 触发标题降级机制
    # FIXED in V5.3: 旧版降级时未清空sub_title导致残留，现规范处理
    p3 = Project(
        main_title="手术室LED无影灯—明视医疗(已签约)",  # 已采购后的新标题
        sub_title="手术室LED无影灯采购",                  # 原需求名称降级为副标题
        status=STATUS已采购,
        creator_id=chief.id,
        procurement_data={
            **PROCUREMENT_DATA_TEMPLATE,
            "supplier_name": "明视医疗设备公司",
            "contact_person": "张经理",
            "contact_phone": "138-0000-1234",
            "quotation": "¥85,000/台",
            "qualification_desc": "三类医疗器械许可证, ISO13485",
            "delivery_date": "2026-05-20",
            "contract_no": "HT-2026-0417-001",
            "notes": "含安装调试与一年质保",
        },
    )

    # 4) 计划报废 — 历史遗留项目（V5.2版本创建的），JSON字段只含基础5项
    # V5.2遗留逻辑兼容: 缺少扩展字段，get_procurement_data()会自动兜底
    p4 = Project(
        main_title="旧版X光机(待报废)",
        sub_title="放射科X光机采购(2018)",
        status=STATUS计划报废,
        creator_id=chief.id,
        procurement_data={
            "supplier_name": "东芝医疗",
            "contact_person": "李工",
            "contact_phone": "021-5555-6666",
            "quotation": "¥320,000",
            "qualification_desc": "注册证号: 2015-222",
            # 注: 无扩展字段(delivery_date/contract_no/notes) — 兜底逻辑会补""
        },
    )

    # 5) 已报废 — 完整数据
    p5 = Project(
        main_title="报废-旧版心电图机",
        sub_title="心电图机采购(2015)",
        status=STATUS已报废,
        creator_id=chief.id,
        procurement_data={
            **PROCUREMENT_DATA_TEMPLATE,
            "supplier_name": "通用医疗",
            "contact_person": "王总",
            "contact_phone": "010-8888-9999",
            "quotation": "¥45,000",
            "qualification_desc": "已注销",
            "notes": "2019年12月正式报废",
        },
    )

    # 员工C创建的需求填报项目（验证普通员工也能创建）
    p6 = Project(
        main_title="药房冷藏柜需求申报",
        sub_title="",
        status=STATUS需求填报,
        creator_id=staff.id,
        procurement_data=None,
    )

    session.add_all([p1, p2, p3, p4, p5, p6])


def main():
    print(f"[V5.3] 初始化数据库: {DB_PATH}")

    # 如果已有旧库，先删除（开发阶段，生产勿用）
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("  -> 已清除旧数据库")

    engine, session = create_engine_and_session()

    users = seed_users(session)
    print(f"  -> 已创建 {len(users)} 个测试用户")
    for u in users:
        print(f"     {u}")

    seed_projects(session, users[0], users[1], users[2])
    print(f"  -> 已创建 6 条测试项目(覆盖全部5种状态)")

    session.commit()
    session.close()

    # 验证
    print("\n── 验证数据 ──")
    _, verify_session = create_engine_and_session()

    all_users = verify_session.query(User).all()
    all_projects = verify_session.query(Project).all()

    for p in all_projects:
        pd = p.get_procurement_data()
        print(f"  {p} | 供应商={pd['supplier_name']} | 扩展字段兜底notes={pd['notes']}")

    verify_session.close()
    print("\n[V5.3] 初始化完成 OK")


if __name__ == "__main__":
    main()