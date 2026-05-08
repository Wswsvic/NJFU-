# seat_filter.py
# 安装依赖: pip install ijson
#
# 用法：
#   1. 将所有楼层的 JSON 响应分别保存为如 response_4f.json, response_5f.json 等
#   2. 或者将所有响应合并保存到一个大文件 seat_all.json
#   3. 修改下方配置，运行脚本

import ijson
import json
import os
from collections import defaultdict

# ==================== 配置区 ====================

# 方式A：如果你把每个楼层的响应存在不同文件
INPUT_FILES = [
    "100455344.txt",
    "100455346.txt",
    "100455350.txt",
    "100455352.txt",
    "100455354.txt",
    "100455356.txt",
    "100455358.txt",
    "100455360.txt",
    "106658017.txt",
    "111488386.txt",
    "111488388.txt",
    "111488396.txt"
]

# 方式B：如果所有楼层合并成一个大文件（多层 data 数组合并）
SINGLE_FILE = None  # 如果不用单文件模式，设为 None
# SINGLE_FILE = None

# 输出文件
OUTPUT_FILE = "seat_summary.csv"  # 汇总表格
OUTPUT_JSONL = "seat_filtered.jsonl"  # 筛选结果（详细）

# 筛选条件（可组合，None 表示不筛选）
FILTERS = {
    "kindName": None,  # 例如 "四层A区" 或 None
    "devStatus": 0,  # 0=空闲, 1=占用, None=不限
    "devName_contains": None,  # 例如 "A001" 或 None
}


# ==================== 核心逻辑 ====================

def process_single_file(filepath, filters, csv_rows, jsonl_fp):
    """
    流式解析单个 JSON 文件，筛取 data 数组中的座位
    """
    filename = os.path.basename(filepath)
    print(f"📂 正在处理: {filename}")

    count_total = 0
    count_matched = 0

    try:
        with open(filepath, 'rb') as f:
            # 流式遍历 data 数组中的每个元素
            seats = ijson.items(f, 'data.item')

            for seat in seats:
                count_total += 1

                if match_filters(seat, filters):
                    count_matched += 1

                    # 提取关键字段
                    row = extract_key_info(seat)
                    row['source_file'] = filename

                    # 写入汇总 CSV
                    csv_rows.append(row)

                    # 写入详细 JSONL（保留完整原始对象）
                    jsonl_fp.write(json.dumps(seat, ensure_ascii=False) + '\n')

    except Exception as e:
        print(f"   ⚠️ 处理出错: {e}")
        return 0, 0

    print(f"   ✅ 共 {count_total} 个座位，匹配 {count_matched} 个")
    return count_total, count_matched


def process_single_file_array(filepath, filters, csv_rows, jsonl_fp):
    """
    如果 JSON 结构是直接的数组 [...]
    """
    filename = os.path.basename(filepath)
    print(f"📂 正在处理: {filename}")

    count_total = 0
    count_matched = 0

    try:
        with open(filepath, 'rb') as f:
            seats = ijson.items(f, 'item')

            for seat in seats:
                count_total += 1

                if match_filters(seat, filters):
                    count_matched += 1
                    row = extract_key_info(seat)
                    row['source_file'] = filename
                    csv_rows.append(row)
                    jsonl_fp.write(json.dumps(seat, ensure_ascii=False) + '\n')

    except Exception as e:
        print(f"   ⚠️ 处理出错: {e}")
        return 0, 0

    print(f"   ✅ 共 {count_total} 个座位，匹配 {count_matched} 个")
    return count_total, count_matched


def match_filters(seat, filters):
    """检查座位是否满足所有筛选条件"""
    if filters.get("devStatus") is not None:
        if seat.get("devStatus") != filters["devStatus"]:
            return False

    if filters.get("kindName") is not None:
        if seat.get("kindName") != filters["kindName"]:
            return False

    if filters.get("devName_contains") is not None:
        if filters.get("devName_contains") not in seat.get("devName", ""):
            return False

    return True


def extract_key_info(seat):
    """从座位对象中提取我们关心的字段"""
    # 解析预约信息
    current_resv = None
    resv_info = seat.get("resvInfo", [])
    if resv_info:
        r = resv_info[0]
        current_resv = {
            "resvId": r.get("resvId"),
            "resvStatus": r.get("resvStatus"),  # 1027 可能是已预约之类的状态
            "userName": r.get("trueName"),
            "startTime": r.get("startTime"),
            "endTime": r.get("endTime"),
        }

    return {
        "devId": seat.get("devId"),
        "devName": seat.get("devName"),
        "kindName": seat.get("kindName"),  # 楼层/区域
        "roomId": seat.get("roomId"),
        "openStart": seat.get("openStart"),
        "openEnd": seat.get("openEnd"),
        "currentReservation": current_resv,
    }


def write_csv(rows, output_file):
    """将提取的数据写入 CSV"""
    if not rows:
        print("⚠️ 没有匹配结果，不生成 CSV")
        return

    # 展平嵌套字段
    fieldnames = [
        "devId", "devName", "kindName", "roomId",
        "openStart", "openEnd",
        "source_file"
    ]

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for row in rows:
            # 展平 currentReservation
            if row.get("currentReservation"):
                cr = row.pop("currentReservation")
                row["currentReservation_resvStatus"] = cr.get("resvStatus")
                row["currentReservation_userName"] = cr.get("userName")
            writer.writerow(row)

    print(f"📊 CSV 已保存: {output_file}")


def print_statistics(csv_rows):
    """打印简单的统计信息"""
    print("\n" + "=" * 50)
    print("📊 统计汇总")
    print("=" * 50)

    print(f"总匹配座位数: {len(csv_rows)}")

    # 按楼层统计
    by_kind = defaultdict(int)
    by_status = defaultdict(int)

    for row in csv_rows:
        by_kind[row.get("kindName", "未知")] += 1
        status = "空闲" if row.get("devStatus") == 0 else "占用"
        by_status[status] += 1

    print("\n按区域分布:")
    for kind, count in sorted(by_kind.items()):
        print(f"  {kind}: {count} 个")

    print("\n按状态分布:")
    for status, count in sorted(by_status.items()):
        print(f"  {status}: {count} 个")


# ==================== 主程序 ====================

def main():
    csv_rows = []

    with open(OUTPUT_JSONL, 'w', encoding='utf-8') as jsonl_fp:
        if SINGLE_FILE:
            # 单文件模式
            # 先尝试检测 JSON 结构
            with open(SINGLE_FILE, 'rb') as f:
                first_char = f.read(1)
                f.seek(0)
                if first_char == b'[':
                    print("检测到顶层数组结构")
                    total, matched = process_single_file_array(
                        SINGLE_FILE, FILTERS, csv_rows, jsonl_fp
                    )
                else:
                    total, matched = process_single_file(
                        SINGLE_FILE, FILTERS, csv_rows, jsonl_fp
                    )
        else:
            # 多文件模式
            grand_total = 0
            grand_matched = 0

            for filepath in INPUT_FILES:
                if not os.path.exists(filepath):
                    print(f"⚠️ 文件不存在，跳过: {filepath}")
                    continue

                # 检测文件结构
                with open(filepath, 'rb') as f:
                    first_char = f.read(1)
                    f.seek(0)
                    if first_char == b'[':
                        t, m = process_single_file_array(filepath, FILTERS, csv_rows, jsonl_fp)
                    else:
                        t, m = process_single_file(filepath, FILTERS, csv_rows, jsonl_fp)

                    grand_total += t
                    grand_matched += m

            print(f"\n🎯 总计: {grand_total} 个座位，匹配 {grand_matched} 个")

    # 输出结果
    write_csv(csv_rows, OUTPUT_FILE)
    print(f"📄 详细数据已保存: {OUTPUT_JSONL}")

    # 打印统计
    print_statistics(csv_rows)

    # 可选：打印部分结果预览
    # if csv_rows:
    #     print("\n📋 前 5 条结果预览:")
    #     for row in csv_rows[:5]:
    #         status = "空闲" if row.get("devStatus") == 0 else "占用"
    #         print(f"  {row['devName']} | {row['kindName']} | {row['roomName']} | {status}")
    #

if __name__ == "__main__":
    main()