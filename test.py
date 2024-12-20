#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def test_user_info(db_path, test_id):
    """测试查询特定用户信息"""
    if not os.path.exists(db_path):
        print(f"错误：找不到数据库文件 {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 精确查找用户
        cursor.execute("""
            SELECT UserName, NickName, Remark, Type, Alias 
            FROM Contact
            WHERE UserName = ?
        """, (test_id,))
        user = cursor.fetchone()
        
        if user:
            print("\n精确匹配结果:")
            print(f"UserName: {user[0]}")
            print(f"NickName: {user[1]}")
            print(f"Remark: {user[2]}")
            print(f"Type: {user[3]}")
            print(f"Alias: {user[4]}")
        else:
            print(f"\n未找到精确匹配用户: {test_id}")
            
            # 2. 模糊查找
            cursor.execute("""
                SELECT UserName, NickName, Remark, Type, Alias 
                FROM Contact
                WHERE UserName LIKE ?
            """, (f"%{test_id}%",))
            similar_users = cursor.fetchall()
            
            if similar_users:
                print("\n模糊匹配结果:")
                for user in similar_users:
                    print(f"\nUserName: {user[0]}")
                    print(f"NickName: {user[1]}")
                    print(f"Remark: {user[2]}")
                    print(f"Type: {user[3]}")
                    print(f"Alias: {user[4]}")
            else:
                print("也未找到相似用户")
                
            # 3. 查看所有wxid_开头的用户示例
            cursor.execute("""
                SELECT UserName, NickName, Remark, Type, Alias 
                FROM Contact
                WHERE UserName LIKE 'wxid_%'
                LIMIT 5
            """)
            wxid_users = cursor.fetchall()
            print("\n示例wxid_用户:")
            for user in wxid_users:
                print(f"\nUserName: {user[0]}")
                print(f"NickName: {user[1]}")
                print(f"Remark: {user[2]}")
                print(f"Type: {user[3]}")
                print(f"Alias: {user[4]}")
                print("-" * 30)
        
        # 4. 查看Contact表的所有字段
        cursor.execute("PRAGMA table_info(Contact)")
        columns = cursor.fetchall()
        print("\nContact表结构:")
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
            
        # 5. 统计信息
        cursor.execute("SELECT COUNT(*) FROM Contact")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM Contact WHERE UserName LIKE 'wxid_%'")
        wxid_count = cursor.fetchone()[0]
        print(f"\n统计信息:")
        print(f"总联系人数: {total}")
        print(f"wxid_用户数: {wxid_count}")
        
    except sqlite3.Error as e:
        print(f"数据库操作出错: {str(e)}")
    finally:
        conn.close()

def main():
    # 使用项目目录下的database文件夹
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "database", "MicroMsg.decrypted.db")
    
    test_id = "wxid_x0ewfqyc89xr21"
    test_user_info(db_path, test_id)

if __name__ == "__main__":
    main() 