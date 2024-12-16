import requests
from bs4 import BeautifulSoup
import multiprocessing

ROOT = "https://eeclass.nthu.edu.tw"
PROCESSES = 10

def get_reports(hw_id, PHPSESSID):
    url = f"{ROOT}/homework/submitList/{hw_id}"
    
    def get_page(page):
        r = requests.get(url, params={"precedence": "ASC", "page": page}, cookies={"PHPSESSID": PHPSESSID})
        if r.status_code != 200:
            raise Exception(f"Failed to get page {page}: {r.status_code}")
        
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", {"id": "submitList_table"})
        tbody = table.find("tbody")
        
        res = []
        
        for tr in tbody.find_all("tr"):
            if tr.get("id") == "noData":
                break
            
            sid = tr.find("div", {"class": "fs-hint"}).text.lower()
            report_id = tr.find("td").find("input").get("value")
            res.append((sid, report_id))
        
        return res
    
    cur_page = 1
    reports = []
    while True:
        page = get_page(cur_page)
        if len(page) == 0:
            break
        
        reports += page
        cur_page += 1
    
    return reports

def submit_report(report_id, score, comment, PHPSESSID):
    audit_page = f"{ROOT}/homework/report/{report_id}/?exerciseAction=auditReport"
    
    r = requests.get(audit_page, cookies={"PHPSESSID": PHPSESSID})
    if r.status_code != 200:
        raise Exception(f"Failed to get report audit page for {report_id}")
    
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        anticsrf = soup.find("input", {"name": "anticsrf"}).get("value")
        # It does not check ajaxauth
        # ajaxauth = soup.find("form", {"id": "homework-audit-setting-form"}).get("action").split("ajaxAuth=")[1]
    except:
        raise Exception(f"Failed to get anticsrf and ajaxauth for {report_id}")

    
    submit_url = f"{ROOT}/homework/report/?reportId={report_id}"
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    score = str(score)
    # eeclass does not accept .0
    if score.endswith(".0"):
        score = score[:-2]
    
    data = {
        "_fmSubmit": "yes",
        "formVer": "3.0",
        "formId": "homework-audit-setting-form",
        "auditScore": score,
        "worthWatch": "",
        "auditNote": comment,
        "reportId": report_id,
        "anticsrf": anticsrf,
    }
    
    r = requests.post(submit_url, headers=headers, data=data, cookies={"PHPSESSID": PHPSESSID})
    # This returns 403 but it is actually submitted
    if '"status":"true"' not in r.text:
        raise Exception(f"Failed to submit report {report_id}: {r.text}")

def submit_proc(sid, score, comment, report_ids, PHPSESSID):
    if sid.lower() not in report_ids:
        print(f"[WARN] No eeclass report for student: {sid}. Skipping...", flush=True)
        return (sid, 1)
    
    if score is None or score < 0 or score > 100:
        print(f"[WARN] Invalid score for student {sid}: {score}. Skipping...", flush=True)
        return (sid, 2)

    report_id = report_ids[sid.lower()]
    try:
        submit_report(report_id, score, comment, PHPSESSID)
    except Exception as e:
        print(f"[ERROR] Failed to submit report for {sid} (report_id: {report_id}, score: {score}): {e}", flush=True)
        return (sid, 3)
    
    print(f"Submitted report for {sid} (report_id: {report_id})", flush=True)
    return (sid, 0)

def main():
    import sys
    import os
    import pydoc
    
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <data.py> <hw_id>")
        exit(1)
    data_script = pydoc.importfile(sys.argv[1])
    get_data = data_script.get_data
    hw_id = sys.argv[2]
    
    if os.environ.get("PHPSESSID") is None:
        print("Please set PHPSESSID via environment variable")
        exit(1)
    PHPSESSID = os.environ["PHPSESSID"]
    
    grades = get_data()
    
    try:
        reports = get_reports(hw_id, PHPSESSID)
        report_ids = dict(reports)
    except Exception as e:
        print(f"[ERROR] Failed to get report list: {e}")
        return

    with multiprocessing.Pool(PROCESSES) as pool:
        res = pool.starmap(
            submit_proc,
            [(sid, score, comment, report_ids, PHPSESSID) for sid, score, comment in grades]
        )
    
    succeed = [sid for sid, r in res if r == 0]
    no_report = [sid for sid, r in res if r == 1]
    invalid_score = [sid for sid, r in res if r == 2]
    failed = [sid for sid, r in res if r == 3]
    
    print(f"Successfully submitted {len(succeed)} reports")
    print(f"No report on eeclass: {no_report}")
    print(f"Invalid score: {invalid_score}")
    print(f"Submission error: {failed}")
    
    
if __name__ == "__main__":
    main()    
    