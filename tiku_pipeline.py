"""
驾校一点通题库提取、解密与自动化处理流水线脚本 (tiku_pipeline.py)
用于题库月度更新、其它车型提取（货车/客车/摩托车）或其它城市题库导出。
"""

import os
import sys
import json
import sqlite3
import argparse
import pandas as pd

# 默认路径配置
DEFAULT_JXEDT_DIR = r"D:\Program Files (x86)\jxedt"
DEFAULT_OUTPUT_DIR = os.path.join(DEFAULT_JXEDT_DIR, "题库导出")
SECRET_KEY = b"jxedt_pc_client_secret"

def decrypt_val(val):
    """XOR 解密函数，还原 jxedt_user.db 中的题目与解析"""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, (bytes, bytearray)):
        out = bytearray(len(val))
        for i in range(len(val)):
            out[i] = val[i] ^ SECRET_KEY[i % len(SECRET_KEY)]
        try:
            return out.decode('utf-8')
        except UnicodeDecodeError:
            return out.decode('gb18030', errors='ignore')
    return str(val)

def format_answer(q_type, answer_true, an1, an2, an3, an4):
    """将数字答案（1/2/3/4/124）转换为通用的 A/B/C/D 格式"""
    ans_str = str(answer_true).strip()
    if q_type == 1: # 判断题
        if ans_str == '1':
            return f"A ({an1})" if an1 else "正确"
        elif ans_str == '2':
            return f"B ({an2})" if an2 else "错误"
        return ans_str
    elif q_type == 2: # 单选题
        mapping = {'1': 'A', '2': 'B', '3': 'C', '4': 'D'}
        return mapping.get(ans_str, ans_str)
    elif q_type == 3: # 多选题
        mapping = {'1': 'A', '2': 'B', '3': 'C', '4': 'D', '5': 'E', '6': 'F'}
        return ''.join(mapping.get(c, c) for c in sorted(ans_str))
    return ans_str

def get_type_name(q_type):
    return {1: "判断题", 2: "单选题", 3: "多选题"}.get(q_type, f"其他({q_type})")

def get_kemu_name(kemu):
    return {1: "科目一", 2: "科目二常识", 4: "科目四"}.get(kemu, f"科目{kemu}")

def run_pipeline(jxedt_dir=DEFAULT_JXEDT_DIR, output_dir=DEFAULT_OUTPUT_DIR, car_type="xc", city_ids=(0, 25, 182)):
    os.makedirs(output_dir, exist_ok=True)
    
    downloaded_db = os.path.join(jxedt_dir, "app", "node_modules", "bak", "question_banks", f"{car_type}.db")
    user_db = os.path.join(jxedt_dir, "resources", "app", "db", "jxedt_user.db")
    
    if not os.path.exists(downloaded_db):
        print(f"[错误] 未找到下载的题库数据库: {downloaded_db}")
        return False
    if not os.path.exists(user_db):
        print(f"[错误] 未找到原厂数据库: {user_db}")
        return False

    print(f"[*] 1. 加载并解密官方解析库: {user_db}")
    conn_user = sqlite3.connect(user_db)
    c_user = conn_user.cursor()
    c_user.execute("SELECT ID, explain, best_explain_new FROM web_note")
    explains = {}
    for qid, exp, best_exp in c_user.fetchall():
        d_exp = decrypt_val(exp)
        d_best = decrypt_val(best_exp).replace('\\n', '\n')
        explains[qid] = d_best if d_best else d_exp
    conn_user.close()
    print(f"    成功解析 {len(explains)} 条官方详解。")

    print(f"[*] 2. 读取最新题库: {downloaded_db}")
    conn_dl = sqlite3.connect(downloaded_db)
    c_dl = conn_dl.cursor()
    
    # 读取名师口诀
    c_dl.execute("SELECT question_id, voiceSubtitles FROM t_app_question_black_board WHERE voiceSubtitles IS NOT NULL AND voiceSubtitles != ''")
    blackboards = dict(c_dl.fetchall())
    
    # 读取视频精讲
    c_dl.execute("SELECT question_id, video_url FROM t_question_video_explain WHERE video_url IS NOT NULL AND video_url != ''")
    videos = dict(c_dl.fetchall())

    # 查询符合车型与城市条件的题目
    city_str = ",".join(map(str, city_ids))
    sql = f"""
        SELECT ID, kemu, Type, Question, An1, An2, An3, An4, AnswerTrue,
               media_url, sinaimg, question_audio, diff_degree, error_rate, LicenseType, gs, cityid, strTppe
        FROM web_note
        WHERE (',' || gs || ',') LIKE '%,{car_type},%'
          AND (category IS NULL OR category IN (0, 1, 2))
          AND cityid IN ({city_str})
        ORDER BY kemu ASC, cast(strTppe as int) ASC, ID ASC
    """
    c_dl.execute(sql)
    rows = c_dl.fetchall()
    conn_dl.close()
    print(f"    提取出符合条件题目共 {len(rows)} 道。")

    records = []
    seq = 1
    for r in rows:
        qid = r[0]
        kemu = r[1]
        qtype = r[2]
        question = r[3]
        an1, an2, an3, an4 = r[4] or "", r[5] or "", r[6] or "", r[7] or ""
        ans_true = r[8] or ""
        media_url, sinaimg = r[9] or "", r[10] or ""
        audio_url = r[11] or ""
        diff_degree = r[12] or 1
        error_rate = r[13] or 0.0
        license_type, gs = r[14] or "", r[15] or ""
        cityid = r[16]

        formatted_ans = format_answer(qtype, ans_true, an1, an2, an3, an4)
        img_link = media_url if media_url else (f"https://wos.58cdn.com.cn/XyVuTsRqXyf/question/{sinaimg}" if sinaimg else "")

        records.append({
            '题号ID': qid,
            '科目代码': kemu,
            '科目': get_kemu_name(kemu),
            '题型': get_type_name(qtype),
            '题目': question,
            '选项A': an1,
            '选项B': an2,
            '选项C': an3,
            '选项D': an4,
            '正确答案': formatted_ans,
            '官方详解': explains.get(qid, ""),
            '名师口诀与技巧': blackboards.get(qid, ""),
            '图片链接': img_link,
            '视频讲解链接': videos.get(qid, ""),
            '语音朗读链接': audio_url,
            '难度等级(1-5)': diff_degree,
            '错误率': f"{round(error_rate * 100, 1)}%" if error_rate else "",
            '范围': "全国通用题" if cityid == 0 else "地方特色题",
            '准驾车型': license_type
        })
        seq += 1

    df = pd.DataFrame(records)
    
    # 导出 Excel
    excel_out = os.path.join(output_dir, f"驾校一点通_{car_type}_题库导出.xlsx")
    with pd.ExcelWriter(excel_out, engine='openpyxl') as writer:
        for km in [1, 4]:
            sub_df = df[df['科目代码'] == km].drop(columns=['科目代码'])
            if len(sub_df) > 0:
                sheet_name = f"科目{km}({len(sub_df)}题)"
                sub_df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"[*] 3. 已生成 Excel 文件: {excel_out}")

    # 导出干净 SQLite DB
    db_out = os.path.join(output_dir, f"驾校一点通_{car_type}_干净题库.db")
    if os.path.exists(db_out):
        os.remove(db_out)
    conn_clean = sqlite3.connect(db_out)
    df.to_sql("questions", conn_clean, index=False)
    conn_clean.execute("CREATE INDEX idx_kemu ON questions(科目代码)")
    conn_clean.execute("CREATE INDEX idx_id ON questions(题号ID)")
    conn_clean.commit()
    conn_clean.close()
    print(f"[*] 4. 已生成 SQLite 数据库: {db_out}")
    print("[*] 流水线执行完毕！")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="驾校一点通题库自动化提取流水线")
    parser.add_argument("--dir", default=DEFAULT_JXEDT_DIR, help="软件安装根目录")
    parser.add_argument("--out", default=DEFAULT_OUTPUT_DIR, help="输出目录")
    parser.add_argument("--car", default="xc", help="车型代码 (xc:小车, hc:货车, kc:客车, mtc:摩托车)")
    args = parser.parse_args()
    run_pipeline(jxedt_dir=args.dir, output_dir=args.out, car_type=args.car)
