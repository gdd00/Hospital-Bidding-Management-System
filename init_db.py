"""医院招投标管理系统 V5.3 - 数据库初始化与测试数据生成

V5.3重构: 新增Group表种子数据，User增加密码+分组外键
密码使用SHA256哈希，默认密码统一为 emp_id 本身(开发阶段)
"""

import sys
import os
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.tables import (
    Base, Group, User, Project,
    PROCUREMENT_DATA_TEMPLATE,
    DEFAULT_GROUPS,
    STATUS需求填报, STATUS寻找供应商, STATUS已采购,
    STATUS计划报废, STATUS已报废,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("HOSPITAL_DB_PATH", os.path.join(BASE_DIR, "hospital.db"))
ENGINE_URL = f"sqlite:///{DB_PATH}"


def hash_password(raw: str) -> str:
    """SHA256哈希密码 — MVP阶段用SHA256，生产环境应换bcrypt
    FIXED in V5.3: 旧版无密码字段，现增加"""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_engine_and_session():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    engine = create_engine(ENGINE_URL, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session()


def seed_groups(session):
    """插入3个默认权限分组"""
    groups = []
    for gname, gdata in DEFAULT_GROUPS.items():
        g = Group(name=gname, permissions=gdata["permissions"])
        session.add(g)
        groups.append(g)
    session.flush()
    return groups


def seed_users(session, groups):
    """插入3个测试用户，密码=工号(开发阶段)"""
    chief_group, purchase_group, staff_group = groups

    users = [
        User(emp_id="EMP001", name="科长A", password_hash=hash_password("EMP001"), group_id=chief_group.id),
        User(emp_id="EMP002", name="采购牛马B", password_hash=hash_password("EMP002"), group_id=purchase_group.id),
        User(emp_id="EMP003", name="员工C", password_hash=hash_password("EMP003"), group_id=staff_group.id),
    ]
    session.add_all(users)
    session.flush()
    return users


def seed_projects(session, chief, purchaser, staff):
    """插入6条覆盖全部状态的测试项目
    V5.3: procurement_data改为数组，多条供应商记录"""

    p1 = Project(
        main_title="ICU监护仪需求申报",
        sub_title="",
        status=STATUS需求填报,
        creator_id=chief.id,
        procurement_data=None,  # 尚无采购记录
    )
    p2 = Project(
        main_title="手术室LED无影灯采购",
        sub_title="",
        status=STATUS寻找供应商,
        creator_id=chief.id,
        # 已有两条供应商记录
        procurement_data=[
            {**PROCUREMENT_DATA_TEMPLATE, "supplier_name": "明视医疗设备公司", "contact_person": "张经理", "contact_phone": "138-0000-1234", "quotation": "¥85,000/台", "qualification_desc": "三类医疗器械许可证"},
            {**PROCUREMENT_DATA_TEMPLATE, "supplier_name": "华康器械有限公司", "contact_person": "赵总", "contact_phone": "139-1111-5678", "quotation": "¥92,000/台", "qualification_desc": "ISO13485认证"},
        ],
    )
    p3 = Project(
        main_title="手术室LED无影灯—明视医疗(已签约)",
        sub_title="手术室LED无影灯采购",
        status=STATUS已采购,
        creator_id=chief.id,
        procurement_data=[
            {**PROCUREMENT_DATA_TEMPLATE, "supplier_name": "明视医疗设备公司", "contact_person": "张经理", "contact_phone": "138-0000-1234", "quotation": "¥85,000/台", "qualification_desc": "三类医疗器械许可证, ISO13485", "delivery_date": "2026-05-20", "contract_no": "HT-2026-0417-001", "notes": "含安装调试与一年质保"},
            {**PROCUREMENT_DATA_TEMPLATE, "supplier_name": "华康器械有限公司", "contact_person": "赵总", "contact_phone": "139-1111-5678", "quotation": "¥92,000/台", "qualification_desc": "ISO13485认证"},
        ],
    )
    p4 = Project(
        main_title="旧版X光机(待报废)",
        sub_title="放射科X光机采购(2018)",
        status=STATUS计划报废,
        creator_id=chief.id,
        # V5.2遗留逻辑兼容: 旧版单个dict格式，get_procurement_list()会自动转为数组
        procurement_data={"supplier_name": "东芝医疗", "contact_person": "李工", "contact_phone": "021-5555-6666", "quotation": "¥320,000", "qualification_desc": "注册证号: 2015-222"},
    )
    p5 = Project(
        main_title="报废-旧版心电图机",
        sub_title="心电图机采购(2015)",
        status=STATUS已报废,
        creator_id=chief.id,
        procurement_data=[
            {**PROCUREMENT_DATA_TEMPLATE, "supplier_name": "通用医疗", "contact_person": "王总", "contact_phone": "010-8888-9999", "quotation": "¥45,000", "qualification_desc": "已注销", "notes": "2019年12月正式报废"},
        ],
    )
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

    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("  -> 已清除旧数据库")
        except PermissionError:
            print("  -> 旧数据库被锁定无法删除，将重建表结构覆盖")

    engine, session = create_engine_and_session()

    groups = seed_groups(session)
    print(f"  -> 已创建 {len(groups)} 个权限分组")
    for g in groups:
        print(f"     {g}")

    users = seed_users(session, groups)
    print(f"  -> 已创建 {len(users)} 个测试用户 (默认密码=工号)")
    for u in users:
        print(f"     {u}")

    seed_projects(session, users[0], users[1], users[2])
    print(f"  -> 已创建 6 条测试项目(覆盖全部5种状态)")

    session.commit()
    session.close()

    # 验证
    print("\n── 验证数据 ──")
    _, verify_session = create_engine_and_session()

    for u in verify_session.query(User).all():
        print(f"  {u}  has_perm(create_project)={u.has_perm('create_project')}")

    for p in verify_session.query(Project).all():
        pd_list = p.get_procurement_list()
        print(f"  {p} | records={len(pd_list)} | suppliers={[r['supplier_name'] for r in pd_list]}")

    verify_session.close()
    print("\n[V5.3] 初始化完成 OK")


if __name__ == "__main__":
    main()
