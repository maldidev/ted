import os
import sys
import json
import re
import msvcrt
from typing import List, Dict, Tuple, Optional
from colorama import init, Fore, Back, Style

# Initialize colorama
init()

class TedConfig:
    def __init__(self):
        self.syntax_rules: Dict[str, List[Tuple[re.Pattern, str]]] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load syntax highlighting rules from ted.conf"""
        config_path = os.path.join(os.path.expanduser("~"), "ted.conf")
        if not os.path.exists(config_path):
            config_path = os.path.join(os.path.dirname(__file__), "ted.conf")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.syntax_rules = self.parse_config(config)
            except Exception as e:
                sys.stderr.write(f"Error loading config: {e}\n")

    def parse_config(self, config: Dict) -> Dict[str, List[Tuple[re.Pattern, str]]]:
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
                        color = pattern["keywords"]
                        compiled_rules.append((re.compile(regex), color))
                    
                    # Strings
                    if "strings" in pattern:
                        regex = r'(\".*?\")|(\'.*?\')'
                        color = pattern["strings"]
                        compiled_rules.append((re.compile(regex), color))
                    
                    # Numbers
                    if "numbers" in pattern:
                        regex = r'\b\d+\b'
                        color = pattern["numbers"]
                        compiled_rules.append((re.compile(regex), color))
                    
                    # Comments
                    if "comments" in pattern:
                        regex = r'#.*$' if file_pattern == "*.py" else r'\/\/.*$'
                        color = pattern["comments"]
                        compiled_rules.append((re.compile(regex), color))
                    
                    # Imports
                    if "import" in pattern:
                        regex = r'\b(import|from)\b' if file_pattern == "*.py" else r'\b(import|require)\b'
                        color = pattern["import"]
                        compiled_rules.append((re.compile(regex), color))
                    
                except Exception as e:
                    sys.stderr.write(f"Error parsing rule: {e}\n")
            rules[file_pattern] = compiled_rules
        return rules

    def get_rules_for_file(self, filename: Optional[str]) -> List[Tuple[re.Pattern, str]]:
        """Get syntax rules for a specific file"""
        if not filename:
            return []
        
        for pattern, rules in self.syntax_rules.items():
            # Convert wildcard pattern to regex
            regex_pattern = pattern.replace('.', '\.').replace('*', '.*').replace('?', '.')
            if re.fullmatch(regex_pattern, os.path.basename(filename)):
                return rules
        return []

    @staticmethod
    def get_color(color_name: str) -> str:
        """Map color names to colorama values"""
        color_map = {
            "black": Fore.BLACK,
            "red": Fore.RED,
            "green": Fore.GREEN,
            "yellow": Fore.YELLOW,
            "blue": Fore.BLUE,
            "magenta": Fore.MAGENTA,
            "cyan": Fore.CYAN,
            "white": Fore.WHITE
        }
        return color_map.get(color_name.lower(), Fore.WHITE)

class Ted:
    def __init__(self, filename: Optional[str] = None):
        self.filename = filename
        self.content: List[str] = [""]
        self.mode = 'normal'
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

    def ensure_cursor_in_bounds(self) -> None:
        """Keep cursor position within valid bounds"""
        self.cursor_y = max(0, min(self.cursor_y, len(self.content) - 1))
        current_line_length = len(self.content[self.cursor_y])
        self.cursor_x = max(0, min(self.cursor_x, current_line_length))

    def clear_screen(self) -> None:
        """Clear the terminal screen"""
        os.system('cls')

    def apply_syntax_highlighting(self, line: str) -> str:
        """Apply syntax highlighting to a line of text"""
        if not self.syntax_rules or not line:
            return line
        
        colored_line = line
        for pattern, color_name in self.syntax_rules:
            color = self.config.get_color(color_name)
            for match in pattern.finditer(line):
                start, end = match.span()
                colored_line = (
                    colored_line[:start] +
                    color + line[start:end] + Fore.RESET +
                    colored_line[end:]
                )
        return colored_line

    def display(self) -> None:
        """Render the editor interface"""
        self.clear_screen()
        self.ensure_cursor_in_bounds()
        
        # Display header
        print(f"{Back.BLUE}{Fore.WHITE}Ted - {self.filename or '[No Name]'}", end='')
        print(f"{' [+]' if self.dirty else ''} | {self.mode.upper()} mode", end='')
        print(f" | Line {self.cursor_y + 1}/{len(self.content)}{Style.RESET_ALL}")
        print("-" * 80)
        
        # Display content around cursor
        start_line = max(0, self.cursor_y - 10)
        end_line = min(len(self.content), self.cursor_y + 10)
        
        for y in range(start_line, end_line):
            line = self.content[y] if y < len(self.content) else ""
            colored_line = self.apply_syntax_highlighting(line)
            
            if y == self.cursor_y:
                print(f"{Back.WHITE}{Fore.BLACK}>{colored_line}{Style.RESET_ALL}")
                print(" " * (self.cursor_x + 1) + "^")
            else:
                print(f" {colored_line}")
        
        print("-" * 80)
        if self.message:
            print(f"{Fore.YELLOW}{self.message}{Style.RESET_ALL}")
            self.message = ""

    def get_key(self) -> str:
        """Get a single key input"""
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch == b'\xe0':  # Extended key code
                    ch = msvcrt.getch()
                    if ch == b'H':
                        return 'KEY_UP'
                    elif ch == b'P':
                        return 'KEY_DOWN'
                    elif ch == b'K':
                        return 'KEY_LEFT'
                    elif ch == b'M':
                        return 'KEY_RIGHT'
                elif ch == b'\r':
                    return 'KEY_ENTER'
                elif ch == b'\x08':
                    return 'KEY_BACKSPACE'
                elif ch == b'\x1b':
                    return 'KEY_ESC'
                else:
                    try:
                        return ch.decode('utf-8')
                    except:
                        continue

    def handle_normal_mode(self, key: str) -> None:
        """Handle key presses in normal mode"""
        if key == 'i':
            self.mode = 'insert'
        elif key == 'h' or key == 'KEY_LEFT':
            self.cursor_x = max(0, self.cursor_x - 1)
        elif key == 'j' or key == 'KEY_DOWN':
            self.cursor_y = min(len(self.content)-1, self.cursor_y + 1)
            self.cursor_x = min(self.cursor_x, len(self.content[self.cursor_y]))
        elif key == 'k' or key == 'KEY_UP':
            self.cursor_y = max(0, self.cursor_y - 1)
            self.cursor_x = min(self.cursor_x, len(self.content[self.cursor_y]))
        elif key == 'l' or key == 'KEY_RIGHT':
            self.cursor_x = min(len(self.content[self.cursor_y]), self.cursor_x + 1)
        elif key == ':':
            self.get_command()
        elif key == 'x':
            if self.cursor_x < len(self.content[self.cursor_y]):
                line = self.content[self.cursor_y]
                self.content[self.cursor_y] = line[:self.cursor_x] + line[self.cursor_x+1:]
                self.dirty = True
        elif key == 'o':
            self.content.insert(self.cursor_y + 1, "")
            self.cursor_y += 1
            self.cursor_x = 0
            self.mode = 'insert'
            self.dirty = True
        elif key == 'O':
            self.content.insert(self.cursor_y, "")
            self.cursor_x = 0
            self.mode = 'insert'
            self.dirty = True
        elif key == '$':
            self.cursor_x = len(self.content[self.cursor_y])
        elif key == '0':
            self.cursor_x = 0
        elif key == 'G':
            self.cursor_y = len(self.content) - 1
            self.cursor_x = min(self.cursor_x, len(self.content[self.cursor_y]))
        elif key == 'g':
            next_key = self.get_key()
            if next_key == 'g':
                self.cursor_y = 0
                self.cursor_x = min(self.cursor_x, len(self.content[self.cursor_y]))
        elif key == 'KEY_ESC':
            pass  # Already in normal mode

    def handle_insert_mode(self, key: str) -> None:
        """Handle key presses in insert mode"""
        if key == 'KEY_ESC':
            self.mode = 'normal'
        elif key == 'KEY_BACKSPACE':
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
        elif key == 'KEY_ENTER':
            line = self.content[self.cursor_y]
            self.content.insert(self.cursor_y + 1, line[self.cursor_x:])
            self.content[self.cursor_y] = line[:self.cursor_x]
            self.cursor_y += 1
            self.cursor_x = 0
            self.dirty = True
        elif key == 'KEY_LEFT':
            self.cursor_x = max(0, self.cursor_x - 1)
        elif key == 'KEY_RIGHT':
            self.cursor_x = min(len(self.content[self.cursor_y]), self.cursor_x + 1)
        elif key == 'KEY_UP':
            self.cursor_y = max(0, self.cursor_y - 1)
            self.cursor_x = min(self.cursor_x, len(self.content[self.cursor_y]))
        elif key == 'KEY_DOWN':
            self.cursor_y = min(len(self.content)-1, self.cursor_y + 1)
            self.cursor_x = min(self.cursor_x, len(self.content[self.cursor_y]))
        elif len(key) == 1 and ord(key) >= 32:  # Printable characters
            line = self.content[self.cursor_y]
            self.content[self.cursor_y] = line[:self.cursor_x] + key + line[self.cursor_x:]
            self.cursor_x += 1
            self.dirty = True

    def get_command(self) -> None:
        """Process command-line commands (starting with :)"""
        print("\n:" + Style.RESET_ALL, end='', flush=True)
        cmd = input()
        self.process_command(cmd)

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
                filename = input(self.message)
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

    def get_filename_for_save(self) -> bool:
        """Prompt for filename to save"""
        self.message = "Enter filename: "
        filename = input(self.message)
        if filename:
            self.filename = filename
            return True
        return False

    def run(self) -> None:
        """Main editor loop"""
        try:
            while not self.quit:
                self.display()
                key = self.get_key()
                
                if self.mode == 'normal':
                    self.handle_normal_mode(key)
                elif self.mode == 'insert':
                    self.handle_insert_mode(key)
        except Exception as e:
            print(f"\nEditor error: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    # Create default config if it doesn't exist
    default_config = {
        "*.py": [
            {
                "keywords": "yellow",
                "keywords_list": ["def", "class", "if", "else", "for", "while", "return", "try", "except"],
                "strings": "green",
                "numbers": "magenta",
                "comments": "cyan",
                "import": "red"
            }
        ],
        "*.js": [
            {
                "keywords": "magenta",
                "keywords_list": ["function", "class", "if", "else", "for", "while", "return", "try", "catch"],
                "strings": "green",
                "numbers": "yellow",
                "comments": "cyan",
                "import": "blue"
            }
        ]
    }

    config_path = os.path.join(os.path.expanduser("~"), "ted.conf")
    if not os.path.exists(config_path):
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)

    filename = sys.argv[1] if len(sys.argv) > 1 else None
    editor = Ted(filename)
    editor.run()