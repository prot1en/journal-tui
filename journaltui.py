import curses
import os
import datetime

JOURNAL_DIR = "journal"
os.makedirs(JOURNAL_DIR, exist_ok=True)

# LOADING NOTE FROM JOURNAL SECTION
def get_entries():
    return sorted(f for f in os.listdir(JOURNAL_DIR) if f.endswith(".txt"))

def load_entry(filename):
    filepath = os.path.join(JOURNAL_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def save_entry(filename, content):
    filepath = os.path.join(JOURNAL_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

def draw_sidebar(stdscr, entry_list, selected_idx, sidebar_scroll, height, width):
    sidebar_width = 20
    sidebar = stdscr.subwin(height, sidebar_width, 0, 0)
    sidebar.box()

    max_visible_entries = height - 2  # -2 because of borders
    visible_entries = entry_list[sidebar_scroll:sidebar_scroll + max_visible_entries]

    for i, entry in enumerate(visible_entries):
        actual_idx = i + sidebar_scroll
        try:
            if actual_idx == selected_idx:
                sidebar.addstr(i + 1, 2, entry[:-4][:sidebar_width - 4], curses.A_REVERSE)
            else:
                sidebar.addstr(i + 1, 2, entry[:-4][:sidebar_width - 4])
        except curses.error:
            stdscr.addstr(1, 22, "ERROR: Writing out of bounds")

    sidebar.refresh()

# WRAPPING TEXT LOGIC
def wrap_text(text, max_width):
    wrapped_lines = []
    for line in text.split("\n"):
        while len(line) > max_width:
            wrapped_lines.append(line[:max_width])
            line = line[max_width:]
        wrapped_lines.append(line)
    return wrapped_lines

def calculate_wrapped_line_index(text, max_width, cursor_line, cursor_col):
    lines = text.split("\n")
    wrapped_lines = []
    wrapped_map = {}  

    line_index = 0
    for i, line in enumerate(lines):
        wrapped_map[i] = line_index 

        while len(line) > max_width:
            wrapped_lines.append(line[:max_width])
            line = line[max_width:]
            line_index += 1 

        wrapped_lines.append(line)
        line_index += 1  

    # Find where the cursor is in the wrapped text
    wrapped_line_index = wrapped_map[cursor_line] + (cursor_col // max_width)
    wrapped_col = cursor_col % max_width

    return wrapped_line_index, wrapped_col


def draw_note_area(stdscr, text, cursor_pos, note_scroll, screen_width, height, width):
    note_x = 22  # starting for note = 20 + 2 because of border
    note_width = width - note_x - 1
    note_height = height - 3  # border
    stdscr.addstr(0, note_x, " Journal-TUI ", curses.A_BOLD | curses.A_REVERSE)

    wrapped_lines = wrap_text(text, note_width - 2)  # wrapping text plus 2 gap for padding

    line_num, col_num = cursor_pos  # x and y of cursor
    lines = text.split("\n")

    wrapped_line_index, wrapped_col = calculate_wrapped_line_index(
        text,
        note_width - 2,
        line_num,
        col_num
    )

    # scrolling logic
    if wrapped_line_index < note_scroll:
        note_scroll = wrapped_line_index
    elif wrapped_line_index >= note_scroll + note_height:
        note_scroll = wrapped_line_index - note_height + 1

    # draw visible lines
    visible_lines = wrapped_lines[note_scroll:note_scroll + note_height]
    for i, line in enumerate(visible_lines):
        stdscr.addstr(i + 2, note_x, line[:note_width - 2])

    # calculate display position
    display_line = wrapped_line_index - note_scroll
    display_col = min(wrapped_col, note_width - 2)


    if 2 <= display_line + 2 < height - 1:  # prevent out-of-bounds movement
        stdscr.move(display_line + 2, note_x + display_col)

    return note_scroll

# no logic just footer for looks
def draw_footer(stdscr, height, width):
    footer_text = " [Ctrl+↑/↓] Move  [Ctrl + N] New Entry  [Esc] Exit "

    x_position = max((width - len(footer_text)) // 2, 0)

    stdscr.attron(curses.A_REVERSE)
    stdscr.addstr(height - 1, x_position, footer_text)
    stdscr.attroff(curses.A_REVERSE)

def main(stdscr):
    height, width = stdscr.getmaxyx()  # getting height and width of screen
    sidebar_scroll = 0
    note_scroll = 0
    wrapped_col = 0
    curses.curs_set(1)
    stdscr.clear()
    stdscr.keypad(True)

    entry_list = get_entries()[::-1]  # reversing entries so newest entry is top
    if not entry_list:  # making new entry if user already doesn't have
        new_date = datetime.date.today().strftime("%Y-%m-%d.txt")
        entry_list.append(new_date)
        save_entry(new_date, "")

    selected_idx = 0
    current_file = entry_list[selected_idx]
    current_text = load_entry(current_file)

    cursor_pos = (0, 0)

    while True:
        stdscr.clear()
        stdscr.border()
        draw_footer(stdscr, height, width)
        draw_sidebar(stdscr, entry_list, selected_idx, sidebar_scroll, height, width)
        note_scroll = draw_note_area(stdscr, current_text, cursor_pos, note_scroll, width, height, width)

        key = stdscr.getch()
        line_num, col_num = cursor_pos
        lines = current_text.split("\n")
        note_width = width - 22 - 1
        note_height = height - 3        
        current_line = lines[line_num]
        max_line_len = note_width - 2            

        if key in (337, 567, 480) and selected_idx > 0:  # Ctrl+Up
            selected_idx -= 1
            if selected_idx < sidebar_scroll:
                sidebar_scroll = max(0, sidebar_scroll - 1)
            current_file = entry_list[selected_idx]
            current_text = load_entry(current_file)
            cursor_pos = (0, 0)  # Reset cursor position
            note_scroll = 0  # Reset note scroll

        elif key in (336, 526, 481) and selected_idx < len(entry_list) - 1:  # Ctrl+Down
            selected_idx += 1
            if selected_idx >= sidebar_scroll + (height - 2):
                sidebar_scroll = min(len(entry_list) - (height - 2), sidebar_scroll + 1)
            current_file = entry_list[selected_idx]
            current_text = load_entry(current_file)
            cursor_pos = (0, 0)  # reset cursor position
            note_scroll = 0  # reset note scroll

        elif key == curses.KEY_UP:
            line_num -= 1 
            if line_num < 0:  
                line_num = 0
            col_num = min(len(lines[line_num]), max_line_len - 1)  # cursor within line bounds


        elif key == curses.KEY_DOWN:
            line_num += 1
            if line_num >= len(lines):
                line_num = max(0, len(lines) - 1)  # keep in range

            col_num = min(col_num, len(lines[line_num]))

        elif key == curses.KEY_LEFT and col_num > 0:
            col_num -= 1

        elif key == curses.KEY_RIGHT and col_num < len(current_line):
            col_num += 1

        elif key in (curses.KEY_BACKSPACE, 127, 8, ord('\b')):  # Backspace
            if col_num > 0:
                lines[line_num] = lines[line_num][:col_num-1] + lines[line_num][col_num:]
                col_num -= 1
                current_text = "\n".join(lines)
            elif line_num > 0:
                prev_line_len = len(lines[line_num-1])
                lines[line_num-1] += lines[line_num]
                del lines[line_num]
                current_text = "\n".join(lines)
                line_num -= 1
                col_num = prev_line_len

        elif key in (curses.KEY_ENTER, 10, 13):  # Enter
            new_line = lines[line_num][col_num:]
            lines[line_num] = lines[line_num][:col_num]
            lines.insert(line_num + 1, new_line)
            current_text = "\n".join(lines)
            line_num += 1              
            col_num = 0    

        elif 32 <= key <= 126:
            lines[line_num] = lines[line_num][:col_num] + chr(key) + lines[line_num][col_num:]
            col_num += 1
            current_text = "\n".join(lines)

        cursor_pos = (line_num, col_num)
        save_entry(current_file, current_text)

        if key == 27:  # ESC key
            break

        if key == 14:  # Ctrl+N
            new_date = datetime.date.today().strftime("%Y-%m-%d.txt")
            if new_date not in entry_list:
                entry_list.append(new_date)
                save_entry(new_date, "")
                selected_idx = len(entry_list) - 1
                current_file = new_date
                current_text = ""
                cursor_pos = (0, 0)
            else:
                notice_width = 32
                notice_height = 8
                start_y = height // 2 - notice_height // 2
                start_x = width // 2 - notice_width // 2
                notice_win = stdscr.subwin(notice_height, notice_width, start_y, start_x)
                notice_win.border(0)
                message = "           ALERT            \n\n    You already have a    \n    daily for this date!    \n\nPress any key to continue..."
                for i, line in enumerate(message.split("\n")):
                    if "ALERT" in line:
                        notice_win.addstr(i + 1, 2, line, curses.A_REVERSE)
                    else:
                        notice_win.addstr(i + 1, 2, line)
                notice_win.refresh()
                notice_win.getch()
                notice_win.clear()
                notice_win.refresh()

curses.wrapper(main)

