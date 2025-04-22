import sqlite3
from typing import Tuple

DB_NAME = "bookstore.db"


def connect_db() -> sqlite3.Connection:
    """建立並返回 SQLite 資料庫連線，設置 row_factory = sqlite3.Row."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db(conn: sqlite3.Connection) -> None:
    """檢查並建立資料表，並插入初始資料。"""
    script = """
    CREATE TABLE IF NOT EXISTS member (
        mid TEXT PRIMARY KEY,
        mname TEXT NOT NULL,
        mphone TEXT NOT NULL,
        memail TEXT
    );
    CREATE TABLE IF NOT EXISTS book (
        bid TEXT PRIMARY KEY,
        btitle TEXT NOT NULL,
        bprice INTEGER NOT NULL,
        bstock INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sale (
        sid INTEGER PRIMARY KEY AUTOINCREMENT,
        sdate TEXT NOT NULL,
        mid TEXT NOT NULL,
        bid TEXT NOT NULL,
        sqty INTEGER NOT NULL,
        sdiscount INTEGER NOT NULL,
        stotal INTEGER NOT NULL
    );
    INSERT OR IGNORE INTO member VALUES ('M001', 'Alice', '0912-345678', 'alice@example.com');
    INSERT OR IGNORE INTO member VALUES ('M002', 'Bob', '0923-456789', 'bob@example.com');
    INSERT OR IGNORE INTO member VALUES ('M003', 'Cathy', '0934-567890', 'cathy@example.com');
    INSERT OR IGNORE INTO book VALUES ('B001', 'Python Programming', 600, 50);
    INSERT OR IGNORE INTO book VALUES ('B002', 'Data Science Basics', 800, 30);
    INSERT OR IGNORE INTO book VALUES ('B003', 'Machine Learning Guide', 1200, 20);
    INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal) VALUES (1, '2024-01-15', 'M001', 'B001', 2, 100, 1100);
    INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal) VALUES (2, '2024-01-16', 'M002', 'B002', 1, 50, 750);
    INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal) VALUES (3, '2024-01-17', 'M001', 'B003', 3, 200, 3400);
    INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal) VALUES (4, '2024-01-18', 'M003', 'B001', 1, 0, 600);
    """
    cursor = conn.cursor()
    cursor.executescript(script)
    conn.commit()


def add_sale(
    conn: sqlite3.Connection,
    sdate: str,
    mid: str,
    bid: str,
    sqty: int,
    sdiscount: int,
) -> Tuple[bool, str]:
    """新增銷售記錄，驗證會員、書籍編號和庫存，計算總額並更新庫存。
    回傳 (成功?, 訊息或總額)."""
    cursor = conn.cursor()
    # 驗證會員
    cursor.execute("SELECT 1 FROM member WHERE mid = ?", (mid,))
    if cursor.fetchone() is None:
        return False, "會員編號或書籍編號無效"
    # 驗證書籍
    cursor.execute("SELECT bprice, bstock FROM book WHERE bid = ?", (bid,))
    book_row = cursor.fetchone()
    if book_row is None:
        return False, "會員編號或書籍編號無效"
    price = book_row["bprice"]
    stock = book_row["bstock"]
    # 檢查庫存
    if sqty > stock:
        return False, f"書籍庫存不足 (現有庫存: {stock})"
    # 計算總額
    total = price * sqty - sdiscount
    try:
        with conn:
            conn.execute(
                "INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES (?, ?, ?, ?, ?, ?)",
                (sdate, mid, bid, sqty, sdiscount, total),
            )
            conn.execute(
                "UPDATE book SET bstock = bstock - ? WHERE bid = ?", (sqty, bid)
            )
        return True, str(total)
    except sqlite3.DatabaseError as e:
        return False, f"資料庫錯誤: {e}"


def print_sale_report(conn: sqlite3.Connection) -> None:
    """查詢並顯示所有銷售報表，按銷售編號排序。"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sale.sid, sale.sdate, member.mname, book.btitle, book.bprice,
               sale.sqty, sale.sdiscount, sale.stotal
          FROM sale
          JOIN member ON sale.mid = member.mid
          JOIN book ON sale.bid = book.bid
         ORDER BY sale.sid
        """
    )
    sales = cursor.fetchall()
    if not sales:
        print("沒有銷售記錄")
        return
    print("==================== 銷售報表 ====================")
    for idx, row in enumerate(sales, 1):
        print(f"銷售 #{idx}")
        print(f"銷售編號: {row['sid']}")
        print(f"銷售日期: {row['sdate']}")
        print(f"會員姓名: {row['mname']}")
        print(f"書籍標題: {row['btitle']}")
        print("--------------------------------------------------")
        print("單價\t數量\t折扣\t小計")
        print("--------------------------------------------------")
        price = row["bprice"]
        qty = row["sqty"]
        disc = row["sdiscount"]
        subtotal = row["stotal"]
        print(f"{price}\t{qty}\t{disc}\t{subtotal:,}")
        print("--------------------------------------------------")
        print(f"銷售總額: {subtotal:,}")
        print("==================================================\n")


def update_sale(conn: sqlite3.Connection) -> None:
    """更新銷售記錄的折扣和總額。"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sale.sid, member.mname, sale.sdate
          FROM sale
          JOIN member ON sale.mid = member.mid
         ORDER BY sale.sid
        """
    )
    sales = cursor.fetchall()
    if not sales:
        print("沒有銷售記錄可更新")
        return
    print("======== 銷售記錄列表 ========")
    for idx, row in enumerate(sales, 1):
        print(f"{idx}. 銷售編號: {row['sid']} - 會員: {row['mname']} - 日期: {row['sdate']}")
    print("================================")
    while True:
        choice = input("請選擇要更新的銷售編號 (輸入數字或按 Enter 取消): ")
        if choice == "":
            return
        if not choice.isdigit():
            print("=> 錯誤：請輸入有效的數字")
            continue
        idx = int(choice)
        if idx < 1 or idx > len(sales):
            print("=> 錯誤：請輸入有效的數字")
            continue
        sid = sales[idx - 1]["sid"]
        break
    cursor.execute(
        "SELECT book.bprice, sale.sqty FROM sale JOIN book ON sale.bid = book.bid WHERE sale.sid = ?",
        (sid,),
    )
    row2 = cursor.fetchone()
    price = row2["bprice"]
    qty = row2["sqty"]
    while True:
        new_discount = input("請輸入新的折扣金額：")
        try:
            disc = int(new_discount)
            if disc < 0:
                print("=> 錯誤：折扣金額不能為負數，請重新輸入")
                continue
            break
        except ValueError:
            print("=> 錯誤：折扣金額必須為整數，請重新輸入")
    new_total = price * qty - disc
    try:
        with conn:
            conn.execute(
                "UPDATE sale SET sdiscount = ?, stotal = ? WHERE sid = ?",
                (disc, new_total, sid),
            )
        print(f"=> 銷售編號 {sid} 已更新！(銷售總額: {new_total:,})")
    except sqlite3.DatabaseError as e:
        print(f"=> 錯誤：更新失敗 ({e})")


def delete_sale(conn: sqlite3.Connection) -> None:
    """刪除指定的銷售記錄。"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sale.sid, member.mname, sale.sdate
          FROM sale
          JOIN member ON sale.mid = member.mid
         ORDER BY sale.sid
        """
    )
    sales = cursor.fetchall()
    if not sales:
        print("沒有銷售記錄可刪除")
        return
    print("======== 銷售記錄列表 ========")
    for idx, row in enumerate(sales, 1):
        print(f"{idx}. 銷售編號: {row['sid']} - 會員: {row['mname']} - 日期: {row['sdate']}")
    print("================================")
    while True:
        choice = input("請選擇要刪除的銷售編號 (輸入數字或按 Enter 取消): ")
        if choice == "":
            return
        if not choice.isdigit():
            print("=> 錯誤：請輸入有效的數字")
            continue
        idx = int(choice)
        if idx < 1 or idx > len(sales):
            print("=> 錯誤：請輸入有效的數字")
            continue
        sid = sales[idx - 1]["sid"]
        break
    try:
        with conn:
            conn.execute("DELETE FROM sale WHERE sid = ?", (sid,))
        print(f"=> 銷售編號 {sid} 已刪除")
    except sqlite3.DatabaseError as e:
        print(f"=> 錯誤：刪除失敗 ({e})")


def main() -> None:
    """主程式流程，顯示選單並根據使用者選擇呼叫對應功能。"""
    conn = connect_db()
    initialize_db(conn)
    while True:
        print("***************選單***************")
        print("1. 新增銷售記錄")
        print("2. 顯示銷售報表")
        print("3. 更新銷售記錄")
        print("4. 刪除銷售記錄")
        print("5. 離開")
        print("**********************************")
        choice = input("請選擇操作項目(Enter 離開)：")
        if choice == "":
            break
        if not choice.isdigit() or not (1 <= int(choice) <= 5):
            print("=> 請輸入有效的選項（1-5）")
            continue
        option = int(choice)
        if option == 1:
            # 新增銷售記錄
            while True:
                sdate = input("請輸入銷售日期 (YYYY-MM-DD)：")
                if len(sdate) == 10 and sdate.count("-") == 2:
                    break
                print("=> 錯誤：日期格式錯誤，請輸入 YYYY-MM-DD")
            mid = input("請輸入會員編號：")
            bid = input("請輸入書籍編號：")
            while True:
                sqty_input = input("請輸入購買數量：")
                try:
                    sqty = int(sqty_input)
                    if sqty <= 0:
                        print("=> 錯誤：數量必須為正整數，請重新輸入")
                        continue
                    break
                except ValueError:
                    print("=> 錯誤：數量或折扣必須為整數，請重新輸入")
            while True:
                sdiscount_input = input("請輸入折扣金額：")
                try:
                    sdiscount = int(sdiscount_input)
                    if sdiscount < 0:
                        print("=> 錯誤：折扣金額不能為負數，請重新輸入")
                        continue
                    break
                except ValueError:
                    print("=> 錯誤：數量或折扣必須為整數，請重新輸入")
            success, msg = add_sale(conn, sdate, mid, bid, sqty, sdiscount)
            if success:
                total_int = int(msg)
                print(f"=> 銷售記錄已新增！(銷售總額: {total_int:,})")
            else:
                print(f"=> 錯誤：{msg}")
        elif option == 2:
            print_sale_report(conn)
        elif option == 3:
            update_sale(conn)
        elif option == 4:
            delete_sale(conn)
        else:  # option == 5
            break
    conn.close()


if __name__ == "__main__":
    main()
