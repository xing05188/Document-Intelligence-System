"""按顺序加载并在 DATABASE_URL 指定的 PostgreSQL 数据库中执行 sql/*.sql 文件。

用法：
  python scripts/recreate_tables.py

脚本会使用项目的 `src.config` 读取 .env 配置并通过 psycopg 连接数据库。
"""
import sys
import os
from pathlib import Path

# 确保可以导入 src 包
ROOT = Path(__file__).resolve().parent.parent
# 确保能直接导入 `src` 包
SRC_DIR = ROOT / "src"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(ROOT))

from src.config import get_config
from src.db.connection import build_conninfo

import psycopg


def find_sql_files(sql_dir: Path):
    files = sorted([p for p in sql_dir.glob("*.sql")])
    # 如果存在 schema_v1.sql，确保它先执行（因为包含 tasks 等核心表定义）
    schema_file = None
    for p in files:
        if p.name == "schema_v1.sql":
            schema_file = p
            break
    if schema_file:
        files.remove(schema_file)
        files.insert(0, schema_file)
    return files


def execute_sql_file(conn, path: Path):
    print(f"--- 执行: {path.name}")
    sql = path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def main():
    sql_dir = ROOT / "sql"
    if not sql_dir.exists():
        print(f"找不到 sql 目录: {sql_dir}")
        return 1

    files = find_sql_files(sql_dir)
    if not files:
        print("未发现任何 .sql 文件")
        return 1

    cfg = get_config()
    if not cfg.database.enabled:
        print("数据库未启用，请检查 .env 中 DB_ENABLED")
        return 1

    conninfo = build_conninfo(cfg)
    print("连接信息已准备（不会打印密码）。尝试连接数据库...")

    try:
        with psycopg.connect(conninfo) as conn:
            for f in files:
                try:
                    execute_sql_file(conn, f)
                except Exception as e:
                    print(f"执行 {f.name} 失败: {e}")
                    return 2
    except Exception as e:
        print(f"连接数据库失败: {e}")
        return 3

    print("所有 SQL 文件执行完成。")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
