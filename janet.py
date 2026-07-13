import gradio as gr
import pandas as pd
import os
import glob
from datetime import datetime, timedelta
import urllib.request
from ics import Calendar

# Comment bank logic

def list_comment_files():
    # Automatically scan for any custom user feedback files matching the pattern
    files = glob.glob("comments_*.txt")
    if not files:
        # Generate an out-of-the-box template if none exist on launch
        default_name = "comments_assignment1.txt"
        default_content = (
            "[OPENING]\n"
            "Great effort on this assignment!\n"
            "Thank you for submitting your work.\n"
            "Solid analytical breakdown here.\n"
            "[CRITIQUE]\n"
            "Please double check your formatting and APA/MLA citations.\n"
            "Make sure to fully expand on your topic sentences.\n"
            "The conclusion felt a bit rushed; try to summarize all key points.\n"
            "Watch out for grammar and minor proofreading slips."
        )
        try:
            with open(default_name, "w", encoding="utf-8") as f:
                f.write(default_content)
            files = [default_name]
        except Exception:
            pass
    return sorted(files)

def load_comment_template(filename):
    if not filename or not os.path.exists(filename):
        return {}
    
    sections = {}
    current_section = None
    
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("[") and line.endswith("]"):
                    current_section = line[1:-1].strip()
                    sections[current_section] = []
                    continue
                
                if current_section:
                    sections[current_section].append(line)
    except Exception:
        pass
    return sections

def dynamic_render_template(filename):
    # Enforces the generation of a default file template instantly if server tracking arrays are missing
    if not filename:
        files = list_comment_files()
        if files:
            filename = files[0]
            
    sections = load_comment_template(filename)
    
    if not sections:
        return gr.update(visible=False), *[gr.update(visible=False, choices=[], value=None) for _ in range(10)], None
        
    final_updates = []
    sec_names = list(sections.keys())
    
    # Map the parsed text file lines to the 10 static component layer slots sequentially
    for i in range(10):
        if i < len(sec_names):
            sec_name = sec_names[i]
            items = sections[sec_name]
            
            # Use multi-choice checkbox styles for critique rules, standard choices for everything else
            if "critique" in sec_name.lower() or "injection" in sec_name.lower():
                final_updates.append(gr.update(visible=True, choices=items, value=[], label=f"👉 Select {sec_name}:"))
            else:
                # Pre-select the first text line automatically as a smart default value
                default_val = items[0] if items else None
                final_updates.append(gr.update(visible=True, choices=items, value=default_val, label=f"👉 Choose {sec_name}:"))
        else:
            final_updates.append(gr.update(visible=False, choices=[], value=None, label="Inactive Slot"))
            
    return gr.update(visible=True), *final_updates, filename


def handle_file_upload(file_obj):
    if file_obj is None:
        return gr.update()
    base = os.path.basename(file_obj.name)
    # Ensure it follows the required application layout prefix rules
    if not base.startswith("comments_") or not base.endswith(".txt"):
        base = f"comments_{base}" if not base.endswith(".txt") else f"comments_{base[:-4]}.txt"
    
    try:
        with open(file_obj.name, "r", encoding="utf-8") as src, open(base, "w", encoding="utf-8") as dest:
            dest.write(src.read())
    except Exception:
        pass
        
    updated_files = list_comment_files()
    return gr.update(choices=updated_files, value=base)

def build_student_feedback(name, filename, *dynamic_inputs):
    if not name.strip():
        return "Please input a student name to assemble feedback text."
        
    sections = load_comment_template(filename)
    if not sections:
        return "Invalid or empty template configuration file loaded."
        
    greeting = f"Hi {name.strip()},\n\n"
    body_segments = []
    sec_names = list(sections.keys())
    
    # Loop over inputs safely using a length checker to prevent empty parameter mapping errors
    for idx, sec_name in enumerate(sec_names):
        if idx >= len(dynamic_inputs):
            break
        val = dynamic_inputs[idx]
        if not val:
            continue
            
        if isinstance(val, list):
            if val: # Only add if checkboxes are explicitly selected
                body_segments.append(" ".join(val))
        else:
            if str(val).strip():
                body_segments.append(str(val).strip())
            
    main_body = " ".join(body_segments)
    clean_body = main_body.replace("  ", " ").strip()
    return f"{greeting}{clean_body}"

def append_to_batch(name, score, comment, current_state):
    # Initializes empty browser memory lists if None
    if current_state is None:
        current_state = []
    if not name.strip():
        return current_state, pd.DataFrame(current_state, columns=["Name", "Grade/Score", "Feedback Comment"]), None
        
    current_state.append([name.strip(), score, comment])
    df = pd.DataFrame(current_state, columns=["Name", "Grade/Score", "Feedback Comment"])
    
    # Save a scratchpad copy locally for immediate download, overwritten with each click
    batch_path = "session_batch_grades.csv"
    df.to_csv(batch_path, index=False, encoding="utf-8-sig")
    return current_state, df, batch_path

def clear_session_batch():
    return [], pd.DataFrame(columns=["Name", "Grade/Score", "Feedback Comment"]), gr.update(value=None)

def handle_file_dropdown_change(filename):
    # Runs the original load function to get the dropdown list choices
    openings_update, critiques_update = load_comment_template(filename)
    
    # Verifies if the file path is active, and provides it to the download widget
    file_path = filename if filename and os.path.exists(filename) else None
    
    return openings_update, critiques_update, file_path

# Grade Scale logic

CONFIG_FILE = "grade_scale.txt"

def load_grade_scale():
    # Default parameters written automatically if the configuration text file is missing
    defaults = [
        "MAX_POINTS=1000",
        "93=4.0,A", "90=3.7,A-", "87=3.3,B+", "83=3.0,B", "80=2.7,B-",
        "77=2.3,C+", "73=2.0,C", "70=1.7,C-", "67=1.3,D+", "63=1.0,D",
        "60=0.7,D-", "0=0.0,F"
    ]
    
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(defaults))
        except Exception:
            pass
        raw_lines = defaults
    else:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                raw_lines = [line.strip() for line in f if line.strip()]
        except Exception:
            raw_lines = defaults

    scale_rules = []
    max_points = 1000.0  # Safe internal fallback parameter value
    
    for line in raw_lines:
        try:
            if line.startswith("MAX_POINTS="):
                max_points = float(line.split("=")[1].strip())
                continue
            if "=" in line and "," in line:
                pct_part, metrics_part = line.split("=")
                gpa_part, letter_part = metrics_part.split(",")
                scale_rules.append({
                    "min_pct": float(pct_part.strip()),
                    "gpa": float(gpa_part.strip()),
                    "letter": letter_part.strip()
                })
        except Exception:
            continue
            
    scale_rules.sort(key=lambda x: x["min_pct"], reverse=True)
    
    # If parsing completely failed, force-return default framework parameters
    if not scale_rules:
        return load_grade_scale()
        
    return scale_rules, max_points

def get_us_holidays(year):
    holidays = {
        datetime(year, 1, 1).date(): "New Year's Day",
        datetime(year, 7, 4).date(): "Independence Day",
        datetime(year, 11, 11).date(): "Veterans Day",
        datetime(year, 12, 25).date(): "Christmas Day",
    }
    to_may = datetime(year, 5, 31).date()
    holidays[to_may - timedelta(days=(to_may.weekday() - 0) % 7)] = "Memorial Day"
    from_sept = datetime(year, 9, 1).date()
    holidays[from_sept + timedelta(days=(0 - from_sept.weekday()) % 7)] = "Labor Day"
    from_nov = datetime(year, 11, 1).date()
    first_thu = from_nov + timedelta(days=(3 - from_nov.weekday()) % 7)
    holidays[first_thu + timedelta(weeks=3)] = "Thanksgiving"
    return holidays

def build_calendar(start_str, end_str, days_list, target_day_1, recur_pattern_1, target_day_2, recur_pattern_2, ics_url, ics_file):
    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
    except Exception:
        return pd.DataFrame()
        
    days_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
    selected_weekdays = [days_map[d] for d in days_list if d in days_map]
    target_weekday_1 = days_map.get(target_day_1, 0)
    target_weekday_2 = days_map.get(target_day_2, 0)
    
    ics_events = {}
    ics_content = None

    # Source Priority: File Upload -> URL Input
    if ics_file is not None:
        try:
            with open(ics_file.name, 'r', encoding='utf-8') as f:
                ics_content = f.read()
        except Exception:
            pass
    elif ics_url and ics_url.strip():
        try:
            req = urllib.request.Request(ics_url.strip(), headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                ics_content = response.read().decode('utf-8')
        except Exception:
            pass

    if ics_content:
        try:
            cal = Calendar(ics_content)
            for event in cal.events:
                ev_date = event.begin.date()
                if ev_date not in ics_events:
                    ics_events[ev_date] = []
                if event.name and event.name not in ics_events[ev_date]:
                    ics_events[ev_date].append(event.name)
        except Exception:
            pass

    holidays = get_us_holidays(start_date.year)
    patterns_1 = [p.strip() for p in recur_pattern_1.split(",") if p.strip()]
    patterns_2 = [p.strip() for p in recur_pattern_2.split(",") if p.strip()]
    
    rows = []
    current = start_date
    week_num = 1
    last_week_seen = None
    
    while current <= end_date:
        if current.weekday() in selected_weekdays:
            current_year, current_wk, _ = current.isocalendar()
            
            if last_week_seen is not None and last_week_seen != (current_year, current_wk):
                week_num += 1
                display_week = f"Week {week_num}"
            elif last_week_seen is None:
                display_week = f"Week {week_num}"
            else:
                display_week = ""
                
            last_week_seen = (current_year, current_wk)
            day_str = current.strftime('%a %m/%d').upper().replace(' 0', ' ')
            
            topic_items = []
            if current in holidays:
                topic_items.append(holidays[current])
            if current in ics_events:
                topic_items.extend(ics_events[current])
            topic_str = " / ".join(topic_items) if topic_items else ""

            due_1 = ", ".join([p.replace("#", str(week_num)) for p in patterns_1]) if current.weekday() == target_weekday_1 else ""
            due_2 = ", ".join([p.replace("#", str(week_num)) for p in patterns_2]) if current.weekday() == target_weekday_2 else ""

            rows.append([display_week, day_str, topic_str, due_1, due_2])
            
        current += timedelta(days=1)
        
    return pd.DataFrame(rows, columns=["Week #", "Date", "Topic", "Item Due 1", "Item Due 2"])


def run_comments(op, crit, custom):
    crit_str = " ".join(crit) if crit else ""
    return f"{op} {crit_str} {custom}".replace("  ", " ").strip()

def check_and_append_assignment(name, pts, pct):
    """Global helper function to cleanly validate optional assignment strings."""
    if name and str(name).strip() and pts is not None and float(pts) > 0:
        return f"Complete the {str(name).strip()} (Worth {int(pts)} points or {int(pct)}% of your grade)"
    return None

def run_reminders(current_wk_num, greeting_txt, context_txt, reading_topic, due_day_1, due_time_1, read_assign_name, read_assign_pts, read_assign_pct, due_day_2, due_time_2, assign_1_name, assign_1_pts, assign_1_pct, assign_2_name, assign_2_pts, assign_2_pct, assign_3_name, assign_3_pts, assign_3_pct, assign_4_name, assign_4_pts, assign_4_pct, middle_closing_txt, main_closing_txt, instructor_signoff, anchor_date_str):
    try:
        base_date = datetime.strptime(anchor_date_str, "%Y-%m-%d").date()
    except Exception:
        base_date = datetime.now().date()
        
    days_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
    monday_of_week = base_date - timedelta(days=base_date.weekday())
    
    # Calculate Deadline 1
    t1_wd = days_map.get(due_day_1, 0)
    target_date_1 = monday_of_week + timedelta(days=t1_wd)
    date_str_1 = target_date_1.strftime("%A %B %d, %Y")
    
    # Calculate Deadline 2
    t2_wd = days_map.get(due_day_2, 4)
    target_date_2 = monday_of_week + timedelta(days=t2_wd)
    date_str_2 = target_date_2.strftime("%A %B %d, %Y")

    # Assemble Header & Custom Narrative Text
    header = f"Week {int(current_wk_num)}: What to Do\n\n"
    output = header + f"{greeting_txt.strip()},\n\n" + f"{context_txt.strip()}\n\n"
    
    # Render Reading Section 1 (with optional task)
    output += f"Here's what you need to accomplish by the end of the day on {date_str_1} before {due_time_1.strip()}:\n\n"
    output += f"1. Read {reading_topic.strip()}\n"
    
    read_task = check_and_append_assignment(read_assign_name, read_assign_pts, read_assign_pct)
    if read_task:
        output += f"2. {read_task}\n"
    output += "\n"
    
    # Process Optional Assignments for Deadline 2
    assignments_list = []
    assignments_list.append(f"Review the Week {int(current_wk_num)} module")

    a1 = check_and_append_assignment(assign_1_name, assign_1_pts, assign_1_pct)
    if a1: 
        assignments_list.append(a1)
        
    a2 = check_and_append_assignment(assign_2_name, assign_2_pts, assign_2_pct)
    if a2: 
        assignments_list.append(a2 + " Remember: ONLY the POST is due this week, replies are due NEXT week")
        
    a3 = check_and_append_assignment(assign_3_name, assign_3_pts, assign_3_pct)
    if a3: 
        assignments_list.append(a3)
        
    a4 = check_and_append_assignment(assign_4_name, assign_4_pts, assign_4_pct)
    if a4: 
        assignments_list.append(a4)

    # Render Deliverables Section 2
    output += f"Here's what you need to do by {date_str_2} before {due_time_2.strip()}:\n\n"
    for idx, item in enumerate(assignments_list, start=1):
        output += f"{idx}. {item}\n"
    output += "\n"
    
    # Append Custom Closing Blocks
    output += f"{middle_closing_txt.strip()}\nThanks,\n\n\n\n"
    output += f"{main_closing_txt.strip()}\n\n{instructor_signoff.strip()}"
    
    return output

def generate_and_save(start_str, end_str, days_list, target_day_1, recur_pattern_1, target_day_2, recur_pattern_2, ics_url, ics_file):
    df = build_calendar(start_str, end_str, days_list, target_day_1, recur_pattern_1, target_day_2, recur_pattern_2, ics_url, ics_file)
    if df.empty:
        empty_df = pd.DataFrame(columns=["Week #", "Date", "Topic", "Item Due 1", "Item Due 2"])
        return empty_df, "<p style='color:red;'>No table generated yet.</p>", None

    
    csv_path = "generated_calendar.csv"
    df.to_csv(csv_path, index=False)
    
    html_view = make_html_table(df)
    return df, html_view, csv_path

def export_modified_dataframe(df):
    if df is None or df.empty:
        return "<p style='color:red;'>No table generated yet.</p>", None
    
    csv_path = "edited_calendar.csv"
    df.to_csv(csv_path, index=False)
    
    html_view = make_html_table(df)
    return html_view, csv_path

def load_preset_link():
    return "SET PRESET ICS link on LN 425 of janet.py"



# Converts a Pandas DataFrame into a clean, copy-paste friendly HTML table
def make_html_table(df):
    # color: #222222 forces dark text on cells across all dark/light browser templates
    html = '<table border="1" style="border-collapse: collapse; width: 100%; font-family: sans-serif; color: #222222;">'
    # Headers
    html += '<tr style="background-color: #e6e6e6; text-align: left;">'
    for col in df.columns:
        html += f'<th style="padding: 8px; border: 1px solid #cccccc; font-weight: bold; color: #222222;">{col}</th>'
    html += '</tr>'
    # Rows
    for _, row in df.iterrows():
        html += '<tr style="background-color: #ffffff;">'
        for val in row:
            html += f'<td style="padding: 8px; border: 1px solid #dddddd; color: #222222;">{val}</td>'
        html += '</tr>'
    html += '</table>'
    return html


def list_boundary_files():
    # Automatically scan for files matching the required system pattern prefix
    files = glob.glob("boundaries_*.txt")
    if not files:
        # Pre-seed the system default missing assignment text template file if empty
        default_name = "boundaries_missing_assignment_warning.txt"
        default_content = (
            "[Email Template]\n"
            "Hi {NAME},\n"
            "This is one final reminder that you haven't turned in the {ASSIGNMENT}. "
            "This was due by {TIME_1} on {DATE_1}. You were automatically granted an "
            "extension until today {DATE_2} at {TIME_2}. After that, the assignment will "
            "permanently lock and you won't be given a chance to make up this quiz.\n\n"
            "If you're still working on this, that's totally fine, but make sure you do "
            "not miss this submission window, so you don't lose points. If you need to "
            "talk about this, please send me an email or reply to this message.\n\n"
            "Thanks,\n"
            "{SIGN_OFF}"
        )
        try:
            with open(default_name, "w", encoding="utf-8") as f:
                f.write(default_content)
            files = [default_name]
        except Exception:
            pass
    return sorted(files)

def handle_boundary_upload(file_obj):
    if file_obj is None:
        return gr.update()
    base = os.path.basename(file_obj.name)
    if not base.startswith("boundaries_") or not base.endswith(".txt"):
        base = f"boundaries_{base}" if not base.endswith(".txt") else f"boundaries_{base[:-4]}.txt"
    try:
        with open(file_obj.name, "r", encoding="utf-8") as src, open(base, "w", encoding="utf-8") as dest:
            dest.write(src.read())
    except Exception:
        pass
    return gr.update(choices=list_boundary_files(), value=base)

def handle_boundary_dropdown_change(filename):
    if not filename or not os.path.exists(filename):
        return "", None
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        return content, filename
    except Exception:
        return "", None

def build_boundary_email_from_editor(student_name, assignment_name, due_day_1, time_1, due_day_2, time_2, signoff_name, anchor_date_str, live_editor_text):
    if not live_editor_text.strip():
        return "The live template editor box is empty. Please type or load a scenario template."
        
    try:
        base_date = datetime.strptime(anchor_date_str, "%Y-%m-%d").date()
    except Exception:
        base_date = datetime.now().date()
        
    days_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
    monday_of_week = base_date - timedelta(days=base_date.weekday())
    
    # Calculate original deadline date string (Format: Friday 7/10)
    wd_1 = days_map.get(due_day_1, 4)
    target_date_1 = monday_of_week + timedelta(days=wd_1)
    date_str_1 = f"{due_day_1} {target_date_1.month}/{target_date_1.day}"
    
    # Calculate automated extension date string (Format: Monday 7/13)
    wd_2 = days_map.get(due_day_2, 0)
    target_date_2 = monday_of_week + timedelta(days=wd_2)
    date_str_2 = f"{due_day_2} {target_date_2.month}/{target_date_2.day}"
    
    clean_template = live_editor_text
    if clean_template.strip().startswith("["):
        lines = clean_template.split("\n")
        clean_template = "\n".join(lines[1:])
        
    email_output = clean_template.replace("{NAME}", student_name.strip() if student_name.strip() else "There")
    email_output = email_output.replace("{ASSIGNMENT}", assignment_name.strip())
    email_output = email_output.replace("{DATE_1}", date_str_1)
    email_output = email_output.replace("{TIME_1}", time_1.strip())
    email_output = email_output.replace("{DATE_2}", date_str_2)
    email_output = email_output.replace("{TIME_2}", time_2.strip())
    email_output = email_output.replace("{SIGN_OFF}", signoff_name.strip())
    
    return email_output



# ----------------------------------------------------
# INTERFACE 
# ----------------------------------------------------
with gr.Blocks(title="Janet") as app:
    gr.Markdown(
        """
        # Janet 👩‍🏫
        ### 🎵 Don't tell me to 'can it,' Janet 🎵  | (not a girl.)
        """
    )
    with gr.Tabs():
        # TAB 1: AGENDA CALENDAR GENERATOR
        with gr.TabItem("📆 1. Calendar Generator"):
            gr.Markdown("### Syllabus Calendar Generator")
            with gr.Row():
                with gr.Column():
                    start_in = gr.Textbox(label="Start Date (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))
                    end_in = gr.Textbox(label="End Date (YYYY-MM-DD)", value=(datetime.now() + timedelta(weeks=16)).strftime("%Y-%m-%d"))
                    days_in = gr.CheckboxGroup(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], value=["Monday", "Wednesday"], label="Class Schedule Days")
                    
                    with gr.Row():
                        with gr.Column():
                            day_target_1 = gr.Dropdown(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], value="Monday", label="Due Box 1 Assignment Day")
                            recur_in_1 = gr.Textbox(label="Recurring Sequence Format 1 (uses #)", value="Unit # Quiz")
                        with gr.Column():
                            day_target_2 = gr.Dropdown(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], value="Wednesday", label="Due Box 2 Assignment Day")
                            recur_in_2 = gr.Textbox(label="Recurring Sequence Format 2 (uses #)", value="Discussion #, Reply #")
                    
                    # Clean Options for ICS Selection
                    gr.Markdown("### 📅 ICS Calendar Overlay Options")
                    preset_btn = gr.Button("🔗 Use Modern Campus Preset Link", variant="primary")
                    ics_in = gr.Textbox(label="Custom ICS Web Overlay URL Link", value="")
                    ics_file_in = gr.File(label="Upload Local Manual .ICS File", file_types=[".ics"])
                    
                    cal_btn = gr.Button("Generate Agenda Matrix", variant="primary")
                with gr.Column():
                    # Dual View Layout for Editing vs Copy/Pasting
                    with gr.Tabs():
                        with gr.TabItem("✏️ Edit Table"):
                            gr.Markdown("👇 **Double-click any cell below to type edit text changes directly:**")
                            cal_out = gr.Dataframe(
                                headers=["Week #", "Date", "Topic", "Item Due 1", "Item Due 2"],
                                datatype=["str", "str", "str", "str", "str"],
                                interactive=True,
                                label="Editable Course Schedule Matrix"
                            )
                        
                        with gr.TabItem("📋 Select & Copy Table"):
                            gr.Markdown("👇 **Highlight, click-and-drag across the table below to select and copy straight into Canvas or Word:**")
                            cal_html_out = gr.HTML(value='<p style="color:gray;">No table generated yet.</p>')
                    
                    cal_download = gr.File(label="📥 Download Calendar CSV for Excel")
            
            # Wire up preset button click interaction
            preset_btn.click(fn=load_preset_link, inputs=[], outputs=[ics_in])

            # Clicking generate populates both the dataframe view and the copy-pasteable HTML grid
            cal_btn.click(
                fn=generate_and_save,
                inputs=[start_in, end_in, days_in, day_target_1, recur_in_1, day_target_2, recur_in_2, ics_in, ics_file_in],
                outputs=[cal_out, cal_html_out, cal_download]
            )
            
            # Editing values in the dataframe view instantly refreshes your selection/copy grid
            cal_out.change(
                fn=export_modified_dataframe,
                inputs=[cal_out],
                outputs=[cal_html_out, cal_download]
            )



        # TAB 2: ROSTER GPA CONVERTER
        with gr.TabItem("📊 2. Grade Roster"):
            gr.Markdown("### Student Points-to-GPA Processor")
            
            # Initial baseline reading to populate the startup component field value safely
            _, initial_max_points = load_grade_scale()
            
            with gr.Row():
                with gr.Column():
                    points_input = gr.Textbox(label="Paste Points Column From Excel (One point value per line)", value="1000\n950\n880\n720\n610", lines=12)
                    
                    with gr.Row():
                        # Added customizable maximum total score indicator component box
                        max_points_in = gr.Number(label="Maximum Possible Class Points", value=initial_max_points, precision=1)
                    
                    column_select = gr.CheckboxGroup(
                        choices=["GPA Decimal", "Letter Grade"], 
                        value=["GPA Decimal"], 
                        label="Select Columns to Generate for Excel"
                    )
                    
                    grade_btn = gr.Button("Compute Alphanumeric Metrics Profiles", variant="primary")
                    gr.Markdown("💡 *Tip: You can modify standard baselines inside **`grade_scale.txt`** to change defaults across subsequent app boots.*")
                with gr.Column():
                    gr.Markdown("👇 **Click the copy button in the top right corner of the box below to grab your columns for Excel:**")
                    
                    gpa_column_out = gr.Code(label="Excel Ready Column Vectors", lines=14, language="markdown", interactive=False)
                    roster_download = gr.File(label="📥 Download Grades CSV for Excel")
                    
            def process_grades(points_raw, selected_cols, custom_max_points):
                lines_pts = [p.strip() for p in points_raw.split("\n") if p.strip()][:40]
                results = []
                output_lines = []
                
                # Fetch scale configurations (ignore text file's max points, use active UI field value)
                current_scale, _ = load_grade_scale()
                
                # Protect against zero division runtime crashes
                max_pts_denominator = float(custom_max_points) if custom_max_points and float(custom_max_points) > 0 else 1.0
                
                for i in range(max(40, len(lines_pts))):
                    score_val = 0.0
                    if i < len(lines_pts):
                        try:
                            score_val = float(lines_pts[i])
                        except ValueError:
                            score_val = 0.0
                            
                    # Scale percentages based dynamically on input variable values
                    pct = (score_val / max_pts_denominator) * 100
                    
                    gpa, letter = 0.0, "F"
                    for rule in current_scale:
                        if pct >= rule["min_pct"]:
                            gpa = rule["gpa"]
                            letter = rule["letter"]
                            break
                    
                    gpa_str = f"{gpa:.1f}"
                    results.append([int(score_val), gpa_str, letter])
                    
                    row_data = []
                    if "GPA Decimal" in selected_cols:
                        row_data.append(gpa_str)
                    if "Letter Grade" in selected_cols:
                        row_data.append(letter)
                        
                    output_lines.append("\t".join(row_data))
                    
                df = pd.DataFrame(results[:40], columns=["Points", "GPA Decimal", "Letter Grade"])
                csv_path = "converted_grades.csv"
                df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                
                final_text_lines = output_lines[:len(lines_pts)] if lines_pts else output_lines
                clipboard_payload = "\n".join(final_text_lines) if selected_cols else "Please select at least one column metric checkbox."
                
                return clipboard_payload, csv_path

            # Included the maximum points variable input targeting to the calculation trigger loop
            grade_btn.click(
                process_grades, 
                inputs=[points_input, column_select, max_points_in], 
                outputs=[gpa_column_out, roster_download]
            )



        # TAB 3: GRADING COMMENT GENERATOR
        with gr.TabItem("📝 3. Feedback Generator"):
            gr.Markdown("### Adaptive Feedback Processing Engine")
            
            batch_state = gr.State(value=[])
            initial_files = list_comment_files()
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 🧑‍🎓 Active Student Record")
                    student_name = gr.Textbox(label="Student Name:", placeholder="Janet")
                    student_score = gr.Number(label="Assigned Points / Grade:", value=100.0, precision=1)
                    
                    # Master container housing our dynamic component mapping layer slots
                    with gr.Column(visible=True) as dynamic_container:
                        gr.Markdown("### 💬 Custom Template Input Elements")
                        slot_0 = gr.Dropdown(visible=False, choices=[], allow_custom_value=True)
                        slot_1 = gr.CheckboxGroup(visible=False, choices=[])
                        slot_2 = gr.Dropdown(visible=False, choices=[], allow_custom_value=True)
                        slot_3 = gr.Dropdown(visible=False, choices=[], allow_custom_value=True)
                        slot_4 = gr.Dropdown(visible=False, choices=[], allow_custom_value=True)
                        slot_5 = gr.Dropdown(visible=False, choices=[], allow_custom_value=True)
                        slot_6 = gr.Dropdown(visible=False, choices=[], allow_custom_value=True)
                        slot_7 = gr.Dropdown(visible=False, choices=[], allow_custom_value=True)
                        slot_8 = gr.Dropdown(visible=False, choices=[], allow_custom_value=True)
                        slot_9 = gr.Dropdown(visible=False, choices=[], allow_custom_value=True)
                    
                    slot_list = [slot_0, slot_1, slot_2, slot_3, slot_4, slot_5, slot_6, slot_7, slot_8, slot_9]
                    generate_comment_btn = gr.Button("Assemble Feedback Text Block", variant="primary")
                    
                with gr.Column(scale=1):
                    gr.Markdown("### 📋 Formatted Output Preview")
                    comment_out = gr.Code(label="Ready to Copy via Markdown Container", language="markdown", interactive=False, lines=10)
                    
                    batch_btn = gr.Button("➕ Append Record to Session Batch Table", variant="primary")
                    
                    gr.Markdown("### 🗃️ Current Session Batch (Browser State Only)")
                    batch_table = gr.Dataframe(
                        headers=["Name", "Grade/Score", "Feedback Comment"],
                        datatype=["str", "number", "str"],
                        interactive=False,
                        label="Volatile Active Roster Grid View"
                    )
                    
                    with gr.Row():
                        batch_download = gr.File(label="📥 Export Session Batch CSV")
                        clear_batch_btn = gr.Button("🗑️ Clear Session Data", variant="secondary")
                        
                    gr.Markdown("### 📂 Template File Manager")
                    with gr.Row():
                        with gr.Column():
                            file_dropdown = gr.Dropdown(
                                choices=initial_files, 
                                value=initial_files[0] if initial_files else None, 
                                label="Select Assignment Text File From Server",
                                allow_custom_value=True
                            )
                            template_download = gr.File(label="📥 Download Currently Selected TXT Template")
                        with gr.Column():
                            upload_box = gr.File(label="Upload New Template (Saves as comments_filename.txt)", file_types=[".txt"])

            # Wire up dropdown option tracking updates
            file_dropdown.change(
                fn=dynamic_render_template, 
                inputs=[file_dropdown], 
                outputs=[dynamic_container] + slot_list + [template_download]
            )
            
            upload_box.upload(fn=handle_file_upload, inputs=[upload_box], outputs=[file_dropdown])
            
            # Safely triggers the layout renderer as the page mounts onto the browser engine
            app.load(
                fn=dynamic_render_template, 
                inputs=[file_dropdown], 
                outputs=[dynamic_container] + slot_list + [template_download]
            )
            
            # Connect execution tracking logic safely linking parameters 
            generate_comment_btn.click(
                fn=build_student_feedback,
                inputs=[student_name, file_dropdown] + slot_list,
                outputs=[comment_out]
            )
            
            # Connect student batch tracking tools
            batch_btn.click(
                fn=append_to_batch,
                inputs=[student_name, student_score, comment_out, batch_state],
                outputs=[batch_state, batch_table, batch_download]
            ).then(
                fn=lambda: ("", 100.0),
                inputs=[],
                outputs=[student_name, student_score]
            )
            
            clear_batch_btn.click(
                fn=clear_session_batch,
                inputs=[],
                outputs=[batch_state, batch_table, batch_download]
            )



        # TAB 4: FRIENDLY CANVAS REMINDERS
        with gr.TabItem("📣 4. Canvas Announcements"):
            gr.Markdown("### Canvas Announcement Generator")
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 🛠️ Announcement Configuration Options")
                    
                    with gr.Row():
                        wk_num = gr.Number(label="Active Class Week Number:", value=2, precision=0)
                        anchor_date = gr.Textbox(label="Reference Date for Due Math (YYYY-MM-DD):", value=datetime.now().strftime("%Y-%m-%d"))
                    
                    greeting_txt = gr.Textbox(label="Custom Greeting Line:", value="Happy Monday Folks")
                    context_txt = gr.Textbox(
                        label="Main Opening Narrative Paragraph:", 
                        value="Thanks to everyone who completed the survey and the first quiz on time, I really appreciate it. This week you have your first discussion post due. Make sure you carefully read the instructions and ask early if you have questions. I'm available if you have questions or need me to look at a rough draft. Make sure you're including direct quotations from the reading to get a passing grade. Because this is a fully online section, please reach out if you are having difficulty accessing Canvas or completing assignments.",
                        lines=5
                    )
                    
                    # Section 1: Readings & Reading-Day Assignment Parameters
                    gr.Markdown("---")
                    gr.Markdown("### 📖 Required Readings & Deadline 1 Tasks")
                    read_topic = gr.Textbox(label="Required Reading Target Topic Name:", value="Unit 2: Power, Privilege, and Diversity")
                    with gr.Row():
                        day_1 = gr.Dropdown(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], value="Monday", label="Deadline 1 Day")
                        time_1 = gr.Textbox(label="Deadline 1 End Time Window:", value="11:59PM")
                    with gr.Row():
                        read_a_name = gr.Textbox(label="Optional Reading-Day Assignment Name:", value="")
                        read_a_pts = gr.Number(label="Points:", value=0, precision=0)
                        read_a_pct = gr.Number(label="Weight %:", value=0, precision=0)
                    
                    # Section 2: Core Assignments Parameters with Deadline 2 sitting at the top
                    gr.Markdown("---")
                    gr.Markdown("### 📝 Core Assignment Deliverables & Deadline 2 Tasks")
                    with gr.Row():
                        day_2 = gr.Dropdown(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], value="Friday", label="Deadline 2 Day")
                        time_2 = gr.Textbox(label="Deadline 2 End Time Window:", value="11:59PM")
                    
                    gr.Markdown("💡 *Clear an assignment name or zero out points to hide it from the final text:*")
                    with gr.Row():
                        a1_name = gr.Textbox(label="Assignment 1 Name:", value="Unit 2 Quiz")
                        a1_pts = gr.Number(label="Points:", value=50, precision=0)
                        a1_pct = gr.Number(label="Weight %:", value=5, precision=0)
                    with gr.Row():
                        a2_name = gr.Textbox(label="Assignment 2 Name:", value="Discussion Post 1")
                        a2_pts = gr.Number(label="Points:", value=100, precision=0)
                        a2_pct = gr.Number(label="Weight %:", value=10, precision=0)
                    with gr.Row():
                        a3_name = gr.Textbox(label="Assignment 3 Name:", value="")
                        a3_pts = gr.Number(label="Points:", value=0, precision=0)
                        a3_pct = gr.Number(label="Weight %:", value=0, precision=0)
                    with gr.Row():
                        a4_name = gr.Textbox(label="Assignment 4 Name:", value="")
                        a4_pts = gr.Number(label="Points:", value=0, precision=0)
                        a4_pct = gr.Number(label="Weight %:", value=0, precision=0)
                        
                    gr.Markdown("---")
                    gr.Markdown("### ✉️ Custom Closing Narrative Text Fields")
                    middle_closing = gr.Textbox(label="Help Invitation Line (Before Thanks):", value="Again, if you need help or are confused about anything in this class, I am available to you via Canvas messages and during my scheduled office hours, please don't hesitate to reach out.", lines=2)
                    main_closing = gr.Textbox(label="Final Sign-Off Line:", value="Thanks, and I hope you have a great week,", lines=1)
                    signoff = gr.Textbox(label="Instructor Signature Name:", value="Dr. Soandso")
                    
                    generate_announcement_btn = gr.Button("Generate Announcement Draft Template", variant="primary")
                    
                with gr.Column(scale=1):
                    gr.Markdown("👇 **Click the copy button in the top right corner of the box below to grab the layout text block:**")
                    rem_out = gr.Code(label="Assembled Canvas Announcement (Ready to Post)", lines=32, language="markdown", interactive=False)
            
            inputs_p4 = [
                wk_num, greeting_txt, context_txt, read_topic, 
                day_1, time_1, read_a_name, read_a_pts, read_a_pct,
                day_2, time_2, 
                a1_name, a1_pts, a1_pct, 
                a2_name, a2_pts, a2_pct,
                a3_name, a3_pts, a3_pct,
                a4_name, a4_pts, a4_pct,
                middle_closing, main_closing, signoff, anchor_date
            ]
            
            generate_announcement_btn.click(
                fn=run_reminders, 
                inputs=inputs_p4, 
                outputs=[rem_out]
            )

        # TAB 5: DIFFICULT STUDENT RESPONDER
        with gr.TabItem("🥫 5. Can it, Janet!"):
            gr.Markdown("### Canned Email Geneator")
            
            initial_boundary_files = list_boundary_files()
            # Safely grab only the first filename element string instead of passing a raw array list
            starting_value = initial_boundary_files[0] if initial_boundary_files else None
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 🛠️ Scenario & Student Records Variable Input")
                    
                    with gr.Row():
                        student_name_p5 = gr.Textbox(label="Student First Name:", placeholder="Janet")
                        assign_name_p5 = gr.Textbox(label="Target Assignment Variable Name:", value="Unit 1 Quiz")
                    
                    with gr.Row():
                        prof_name_p5 = gr.Textbox(label="Your Sign-off Signature Name:", value="Dr. Soandso")
                        anchor_date_p5 = gr.Textbox(label="Reference Date for Math (YYYY-MM-DD):", value=datetime.now().strftime("%Y-%m-%d"))
                    
                    gr.Markdown("---")
                    gr.Markdown("### 📅 Automated Variable Deadline Offsets")
                    with gr.Row():
                        day_1_p5 = gr.Dropdown(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], value="Friday", label="Original Deadline Day")
                        time_1_p5 = gr.Textbox(label="Original End Time Window:", value="11:59PM")
                    with gr.Row():
                        day_2_p5 = gr.Dropdown(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], value="Monday", label="Extension Target Day")
                        time_2_p5 = gr.Textbox(label="Extension End Time Window:", value="11:59PM")
                    
                    gr.Markdown("---")
                    gr.Markdown("### 📂 Boundary Template Repository Options")
                    with gr.Row():
                        with gr.Column():
                            # Replaced full list reference with the isolated starting_value variable string
                            file_dropdown_p5 = gr.Dropdown(
                                choices=initial_boundary_files, 
                                value=starting_value, 
                                label="Select Scenario Text Template From Server",
                                allow_custom_value=True
                            )
                            boundary_template_download = gr.File(label="📥 Download Currently Selected TXT Template")
                        with gr.Column():
                            upload_box_p5 = gr.File(label="Upload Custom Scenario Template (.txt)", file_types=[".txt"])
                    
                    gr.Markdown("---")
                    gr.Markdown("### ✏️ Live Template Content Editor")
                    gr.Markdown("💡 *Modify wording or change bracketed text layout items right here before generating:*")
                    live_template_editor = gr.Textbox(label="Edit Active Template Text Body Structure:", lines=8, placeholder="Template text fields load here...")
                    
                    generate_email_btn = gr.Button("Compose Draft", variant="primary")
                    
                with gr.Column(scale=1):
                    gr.Markdown("👇 **Click the copy button in the top right corner of the box below to grab the layout text block:**")
                    diff_out = gr.Code(label="Assembled Professional Boundary Communication Email", lines=24, language="markdown", interactive=False)
            
            inputs_p5 = [
                student_name_p5,
                assign_name_p5,
                day_1_p5,
                time_1_p5,
                day_2_p5,
                time_2_p5,
                prof_name_p5,
                anchor_date_p5,
                live_template_editor
            ]
            
            file_dropdown_p5.change(
                fn=handle_boundary_dropdown_change, 
                inputs=[file_dropdown_p5], 
                outputs=[live_template_editor, boundary_template_download]
            )
            
            upload_box_p5.upload(
                fn=handle_boundary_upload, 
                inputs=[upload_box_p5], 
                outputs=[file_dropdown_p5]
            )
            
            app.load(
                fn=handle_boundary_dropdown_change, 
                inputs=[file_dropdown_p5], 
                outputs=[live_template_editor, boundary_template_download]
            )
            
            generate_email_btn.click(
                fn=build_boundary_email_from_editor, 
                inputs=inputs_p5, 
                outputs=[diff_out]
            )




# Launch configuration exposed to all subnets and external local IP interfaces
app.launch(
    server_name="0.0.0.0", 
    server_port=7435, 
    show_error=True,
    theme=gr.Theme.from_hub("hmb/wii")
)
