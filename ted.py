#!/usr/bin/env python3

import os
import sys
import curses
import json
import re
from typing import List, Dict, Tuple, Optional

class TedConfig:
    def __init__(self):
        self.syntax_rules: Dict[str, List[Tuple[re.Pattern, int]] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load syntax highlighting rules from ted.conf"""
        config_path = os.path.expanduser("~/.ted.conf")
        if not os.path.exists(config_path):
            config_path = "/etc/ted.conf"
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.syntax_rules = self.parse_config(config)
            except Exception as e:
                sys.stderr.write(f"Error loading config: {e}\n")

    def parse_config(self, config: Dict) -> Dict[str, List[Tuple[re.Pattern, int]]]:
        """Parse the configuration file into syntax rules"""
        rules = {}
        for file_pattern, patterns in config.items():
            compiled_rules = []
            for pattern in patterns:
                try:
                    # Keywords
                    if "keywords" in pattern:
                        kw = pattern.get("keywords_list", 
                                       ["def", "class", "if", "else", "for", "while", "return"])
                        regex = r'\b(' + '|'.join(kw) + r')\b'
                        color = self.get_color(pattern["keywords"])
                        compiled_rules.append((re.compile(regex), color))
                    
                    # Strings
                    if "strings" in pattern:
                        regex = r'(\".*?\")|(\'.*?\')'
                        color = self.get_color(pattern["strings"])
                        compiled_rules.append((re.compile(regex), color))
                    
                    # Numbers
                    if "numbers" in pattern:
                        regex = r'\b\d+\b'
                        color = self.get_color(pattern["numbers"])
                        compiled_rules.append((re.compile(regex), color))
                    
                    # Comments
                    if "comments" in pattern:
                        regex = r'#.*$'
                        color = self.get_color(pattern["comments"])
                        compiled_rules.append((re.compile(regex), color))
                    
                    # Imports
                    if "import" in pattern:
                        regex = r'\b(import|from)\b'
                        color = self.get_color(pattern["import"])
                        compiled_rules.append((re.compile(regex), color))
                    
                except Exception as e:
                    sys.stderr.write(f"Error parsing rule: {e}\n")
            rules[file_pattern] = compiled_rules
        return rules

    @staticmethod
    def get_color(color_name: str) -> int:
        """Map color names to curses color pairs"""
        color_map = {
            "black": curses.COLOR_BLACK,
            "red": curses.COLOR_RED,
            "green": curses.COLOR_GREEN,
            "yellow": curses.COLOR_YELLOW,
            "blue": curses.COLOR_BLUE,
            "magenta": curses.COLOR_MAGENTA,
            "cyan": curses.COLOR_CYAN,
            "white": curses.COLOR_WHITE
        }
        return color_map.get(color_name.lower(), curses.COLOR_WHITE)

class Ted:
    def __init__(self, filename: Optional[str] = None):
        self.filename = filename
        self.content: List[str] = [""]
        self.mode = 'normal'  # 'normal', 'insert', 'visual'
        self.cursor_y = 0
        self.cursor_x = 0
        self.message = ""
        self.quit = False
        self.dirty = False
        self.config = TedConfig()
        self.syntax_rules = self.config.get_rules_for_file(filename)
        
        if filename and os.path.exists(filename):
            with open(filename, 'r') as f:
                self.content = f.read().splitlines()
                if not self.content:
                    self.content = [""]

        # Curses setup
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        
        # Initialize colors
        curses.start_color()
        self.init_colors()
    
    def init_colors(self) -> None:
        """Initialize color pairs for syntax highlighting"""
        # Basic colors
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Status bar
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Message bar
        
        # Syntax highlighting colors
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)    # Keywords
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Strings
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Numbers
        curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Comments
        curses.init_pair(7, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Imports

    def ensure_cursor_in_bounds(self) -> None:
        """Keep cursor position within valid bounds"""
        self.cursor_y = max(0, min(self.cursor_y, len(self.content) - 1))
        self.cursor_x = max(0, min(self.cursor_x, len(self.content[self.cursor_y])))

    def display(self) -> None:
        """Render the editor interface"""
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()
        
        # Status bar
        status = f"Ted - {self.filename or '[No Name]'}{' [+]' if self.dirty else ''}"
        status += f" | {self.mode.upper()} | Line {self.cursor_y + 1}/{len(self.content)}"
        self.stdscr.addstr(height-2, 0, status.ljust(width-1), curses.color_pair(1))
        
        # Message bar
        self.stdscr.addstr(height-1, 0, self.message.ljust(width-1), curses.color_pair(2))
        self.message = ""
        
        # Display content
        start_line = max(0, self.cursor_y - height // 2)
        for y in range(start_line, min(len(self.content), start_line + height - 2)):
            try:
                line = self.content[y]
                self.display_line(y, line, y == self.cursor_y, width)
            except curses.error:
                pass
        
        # Move cursor
        try:
            self.stdscr.move(
                min(self.cursor_y - start_line, height-3),
                min(self.cursor_x, width-2)
            )
        except curses.error:
            pass
        
        self.stdscr.refresh()

    def display_line(self, y: int, line: str, is_current: bool, width: int) -> None:
        """Display a single line with syntax highlighting"""
        if is_current:
            self.stdscr.addstr(y, 0, " " * width, curses.A_REVERSE)
        
        if not self.syntax_rules:
            self.stdscr.addstr(y, 0, line[:width-1])
            return
        
        pos = 0
        for pattern, color_pair in self.syntax_rules:
            for match in pattern.finditer(line):
                start, end = match.span()
                if start > pos:
                    self.stdscr.addstr(y, pos, line[pos:start][:width-1-pos])
                if start < width:
                    attr = curses.color_pair(color_pair)
                    if is_current:
                        attr |= curses.A_REVERSE
                    self.stdscr.addstr(y, start, line[start:end][:width-1-start], attr)
                pos = end
        
        if pos < len(line):
            self.stdscr.addstr(y, pos, line[pos:][:width-1-pos])

    def handle_input(self) -> None:
        """Process user input"""
        key = self.stdscr.getch()
        
        if self.mode == 'normal':
            self.handle_normal_mode(key)
        elif self.mode == 'insert':
            self.handle_insert_mode(key)

    def handle_normal_mode(self, key: int) -> None:
        """Handle key presses in normal mode"""
        self.ensure_cursor_in_bounds()
        height, width = self.stdscr.getmaxyx()
        
        if key == ord('i'):
            self.mode = 'insert'
        elif key == ord('a'):
            self.cursor_x = min(len(self.content[self.cursor_y]), self.cursor_x + 1)
            self.mode = 'insert'
        elif key == ord('h') or key == curses.KEY_LEFT:
            self.cursor_x = max(0, self.cursor_x - 1)
        elif key == ord('j') or key == curses.KEY_DOWN:
            self.cursor_y = min(len(self.content)-1, self.cursor_y + 1)
            self.cursor_x = min(self.cursor_x, len(self.content[self.cursor_y]))
        elif key == ord('k') or key == curses.KEY_UP:
            self.cursor_y = max(0, self.cursor_y - 1)
            self.cursor_x = min(self.cursor_x, len(self.content[self.cursor_y]))
        elif key == ord('l') or key == curses.KEY_RIGHT:
            self.cursor_x = min(len(self.content[self.cursor_y]), self.cursor_x + 1)
        elif key == ord(':'):
            self.get_command()
        elif key == ord('x'):
            if self.cursor_x < len(self.content[self.cursor_y]):
                line = self.content[self.cursor_y]
                self.content[self.cursor_y] = line[:self.cursor_x] + line[self.cursor_x+1:]
                self.dirty = True
        elif key == ord('o'):
            self.content.insert(self.cursor_y + 1, "")
            self.cursor_y += 1
            self.cursor_x = 0
            self.mode = 'insert'
            self.dirty = True
        elif key == ord('O'):
            self.content.insert(self.cursor_y, "")
            self.cursor_x = 0
            self.mode = 'insert'
            self.dirty = True
        elif key == ord('$'):
            self.cursor_x = len(self.content[self.cursor_y])
        elif key == ord('0'):
            self.cursor_x = 0
        elif key == ord('G'):
            self.cursor_y = len(self.content) - 1
            self.cursor_x = min(self.cursor_x, len(self.content[self.cursor_y]))
        elif key == ord('g'):
            next_key = self.stdscr.getch()
            if next_key == ord('g'):
                self.cursor_y = 0
                self.cursor_x = min(self.cursor_x, len(self.content[self.cursor_y]))
        elif key == curses.KEY_RESIZE:
            pass
        elif key == 27:  # ESC
            pass

    def handle_insert_mode(self, key: int) -> None:
        """Handle key presses in insert mode"""
        self.ensure_cursor_in_bounds()
        
        if key == 27:  # ESC
            self.mode = 'normal'
        elif key == curses.KEY_BACKSPACE or key == 127:
            if self.cursor_x > 0:
                line = self.content[self.cursor_y]
                self.content[self.cursor_y] = line[:self.cursor_x-1] + line[self.cursor_x:]
                self.cursor_x -= 1
                self.dirty = True
            elif self.cursor_y > 0:
                self.cursor_x = len(self.content[self.cursor_y-1])
                self.content[self.cursor_y-1] += self.content[self.cursor_y]
                del self.content[self.cursor_y]
                self.cursor_y -= 1
                self.dirty = True
        elif key == curses.KEY_ENTER or key == 10:
            line = self.content[self.cursor_y]
            self.content.insert(self.cursor_y + 1, line[self.cursor_x:])
            self.content[self.cursor_y] = line[:self.cursor_x]
            self.cursor_y += 1
            self.cursor_x = 0
            self.dirty = True
        elif key == curses.KEY_LEFT:
            self.cursor_x = max(0, self.cursor_x - 1)
        elif key == curses.KEY_RIGHT:
            self.cursor_x = min(len(self.content[self.cursor_y]), self.cursor_x + 1)
        elif key == curses.KEY_UP:
            self.cursor_y = max(0, self.cursor_y - 1)
            self.cursor_x = min(self.cursor_x, len(self.content[self.cursor_y]))
        elif key == curses.KEY_DOWN:
            self.cursor_y = min(len(self.content)-1, self.cursor_y + 1)
            self.cursor_x = min(self.cursor_x, len(self.content[self.cursor_y]))
        elif 32 <= key <= 126:  # Printable characters
            line = self.content[self.cursor_y]
            self.content[self.cursor_y] = line[:self.cursor_x] + chr(key) + line[self.cursor_x:]
            self.cursor_x += 1
            self.dirty = True

    def get_command(self) -> None:
        """Process command-line commands (starting with :)"""
        height, width = self.stdscr.getmaxyx()
        cmd = ""
        while True:
            self.stdscr.addstr(height-1, 0, ":" + cmd.ljust(width-2), curses.color_pair(2))
            self.stdscr.move(height-1, len(cmd)+1)
            self.stdscr.refresh()
            
            key = self.stdscr.getch()
            
            if key == curses.KEY_ENTER or key == 10:
                self.process_command(cmd)
                return
            elif key == curses.KEY_BACKSPACE or key == 127:
                cmd = cmd[:-1]
            elif key == 27:  # ESC
                return
            elif 32 <= key <= 126:
                cmd += chr(key)

    def process_command(self, cmd: str) -> None:
        """Execute editor commands"""
        if cmd == "q":
            if self.dirty:
                self.message = "No write since last change (add ! to override)"
            else:
                self.quit = True
        elif cmd == "q!":
            self.quit = True
        elif cmd == "w":
            if self.filename:
                self.save_file()
            else:
                self.message = "Enter filename: "
                filename = self.get_command_input()
                if filename:
                    self.filename = filename
                    self.save_file()
        elif cmd == "wq":
            if self.filename or self.get_filename_for_save():
                self.save_file()
                self.quit = True
        elif cmd.startswith("w "):
            self.filename = cmd[2:].strip()
            self.save_file()
        else:
            self.message = f"Not an editor command: {cmd}"

    def save_file(self) -> None:
        """Save content to file"""
        try:
            with open(self.filename, 'w') as f:
                f.write("\n".join(self.content))
            self.message = f"'{self.filename}' {len(self.content)}L written"
            self.dirty = False
        except Exception as e:
            self.message = f"Error writing file: {str(e)}"

    def cleanup(self) -> None:
        """Restore terminal settings"""
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()

    def run(self) -> None:
        """Main editor loop"""
        try:
            while not self.quit:
                self.display()
                self.handle_input()
        except Exception as e:
            self.cleanup()
            sys.stderr.write(f"Editor error: {str(e)}\n")
            sys.exit(1)
        finally:
            self.cleanup()

if __name__ == "__main__":
    filename = sys.argv[1] if len(sys.argv) > 1 else None
    editor = Ted(filename)
    editor.run()