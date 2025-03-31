import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
import json
import os
import sys
import keyboard
import requests
from tkinter import ttk
from PIL import Image
import tkinter as tk
import tkinter.font as tkfont

class GlossaryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Справочник")
        self.root.geometry("900x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.appearance_mode = "System"
        ctk.set_appearance_mode(self.appearance_mode)
        ctk.set_default_color_theme("blue")
        self.root.configure(bg="#f0f0f0")

        if getattr(sys, 'frozen', False):
            self.data_directory = os.path.dirname(sys.executable)
        else:
            self.data_directory = os.path.dirname(os.path.abspath(__file__))

        self.glossaries = {}
        self.current_glossary = None
        self.open_tabs = set()
        self.tab_modified = {}

        self.notebook = ctk.CTkTabview(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.notebook.configure(command=self.notebook_tab_changed)

        self.menu_bar = ctk.CTkFrame(root)
        self.menu_bar.pack(side="top", fill="x")

        try:
            image = Image.open("icon.ico")
            self.new_icon = ctk.CTkImage(image, size=(20, 20))
        except:
            self.new_icon = None

        self.file_menu = ctk.CTkOptionMenu(self.menu_bar, values=["Новый", "Открыть", "Сохранить", "Сохранить как...", "Выход"],
                                            command=self.file_menu_callback, font=ctk.CTkFont(size=13))
        self.file_menu.pack(side="left", padx=5)

        self.edit_menu = ctk.CTkOptionMenu(self.menu_bar, values=["Добавить термин", "Редактировать термин", "Удалить термин"],
                                            command=self.edit_menu_callback, font=ctk.CTkFont(size=13))
        self.edit_menu.pack(side="left", padx=5)

        self.appearance_menu = ctk.CTkOptionMenu(self.menu_bar, values=["System", "Dark", "Light"],
                                                 command=self.change_appearance_mode, font=ctk.CTkFont(size=13))
        self.appearance_menu.set(self.appearance_mode)
        self.appearance_menu.pack(side="left", padx=5)

        self.download_menu_o_b = ctk.CTkButton(self.menu_bar, text="Загрузить файл", command=self.download_menu,font=ctk.CTkFont(size=14))
        self.download_menu_o_b.pack(side="left", padx=5)

        self.search_frame = ctk.CTkFrame(root)
        self.search_frame.pack(side="bottom", fill="x", pady=5, padx=10)

        self.search_label = ctk.CTkLabel(self.search_frame, text="Поиск:", font=ctk.CTkFont(size=14))
        self.search_label.pack(side="left", padx=5)

        self.search_entry = ctk.CTkEntry(self.search_frame, font=ctk.CTkFont(size=14))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.search_button = ctk.CTkButton(self.search_frame, text="Найти", command=self.search_term_all_files, font=ctk.CTkFont(size=14))
        self.search_button.pack(side="left", padx=5)

        self.search_options_frame = ctk.CTkFrame(self.search_frame)
        self.search_case_sensitive = ctk.BooleanVar()
        self.case_sensitive_check = ctk.CTkCheckBox(self.search_options_frame, text="Учитывать регистр", variable=self.search_case_sensitive)

        self.search_in_terms = ctk.BooleanVar(value=True)
        self.search_in_definitions = ctk.BooleanVar(value=True)
        self.terms_check = ctk.CTkCheckBox(self.search_options_frame, text="Искать в терминах", variable=self.search_in_terms)
        self.definitions_check = ctk.CTkCheckBox(self.search_options_frame, text="Искать в определениях", variable=self.search_in_definitions)

        keyboard.add_hotkey("F9", self.toggle_visibility)
        self.root.bind("<Control-f>", self.focus_search_entry)

        self.load_glossaries()

        self.is_modified = False
        self.is_visible = False

        self.search_results = []
        self.current_search_index = -1

        self.search_results_window = None
        self.search_result_text = None
        self.result_navigation_frame = None
        self.result_index_label = None
        self.next_result_button = None
        self.prev_result_button = None

    def button_callback(self, file):
        git_url = "https://raw.githubusercontent.com/mrHolaDays/fast_guide_app/refs/heads/guides/"
        resp = requests.get(f"{git_url}/{file}")
        if resp.status_code == 200:
            try:
                with open(os.path.join(self.data_directory, file), "wb") as f:
                    f.write(resp.content)
                self.load_glossaries()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")
        else:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл. Статус код: {resp.status_code}")


    def download_menu(self):
        git_url = "https://raw.githubusercontent.com/mrHolaDays/fast_guide_app/refs/heads/guides/"
        self.download_menu_window = ctk.CTkToplevel(self.root)
        self.download_menu_window.title("Загрузка справочников")
        self.download_menu_window.geometry("600x400")

        
        canvas = tk.Canvas(self.download_menu_window, bd=0, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)

      
        scrollbar = ttk.Scrollbar(self.download_menu_window, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        
        self.scrollable_frame = ctk.CTkFrame(canvas)
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        try:
            response = requests.get(f"{git_url}/list.txt")
            response.raise_for_status()
            f_cont = response.text
            file_l = f_cont.split("\n")
            file_list = [e.split("$") for e in file_l]

            for i in file_list:
                if len(i) == 3 and i[2].strip():
                    file_frame = ctk.CTkFrame(self.scrollable_frame)  
                    file_frame.pack(fill="x", padx=10, pady=5)

                    title_label = ctk.CTkLabel(file_frame, text=i[0], font=ctk.CTkFont(size=16, weight="bold"))
                    title_label.pack(anchor="w", padx=5, pady=2)

                    description_label = ctk.CTkLabel(file_frame, text=i[1], font=ctk.CTkFont(size=14))
                    description_label.pack(anchor="w", padx=5, pady=2)

                    download_button = ctk.CTkButton(file_frame,text="Скачать",command=lambda idx=i: self.button_callback(idx[2].strip()))
                    download_button.pack(side="right", padx=5, pady=5)
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке списка файлов: {e}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Неизвестная ошибка: {e}")



    def focus_search_entry(self, event=None):
        self.search_entry.focus_set()
        return "break"

    def file_menu_callback(self, choice):
        if choice == "Новый":
            self.create_new_glossary()
        elif choice == "Открыть":
            self.open_glossary()
        elif choice == "Сохранить":
            self.save_current_glossary()
        elif choice == "Сохранить как...":
            self.save_glossary_as()
        elif choice == "Выход":
            self.on_closing()

    def edit_menu_callback(self, choice):
        if choice == "Добавить термин":
            self.add_term()
        elif choice == "Редактировать термин":
            self.edit_term()
        elif choice == "Удалить термин":
            self.delete_term()

    def change_appearance_mode(self, new_mode):
        self.appearance_mode = new_mode
        ctk.set_appearance_mode(self.appearance_mode)

    def toggle_visibility(self):
        if self.is_visible:
            self.root.withdraw()
            self.is_visible = False
        else:
            self.root.deiconify()
            self.is_visible = True

    def load_glossaries(self):
        for filename in os.listdir(self.data_directory):
            if filename.endswith(".json"):
                filepath = os.path.join(self.data_directory, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.glossaries[filename] = data
                        tab_name = filename[:-5]
                        if tab_name not in self.open_tabs:
                            self.create_tab(filename)
                            self.open_tabs.add(tab_name)
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось загрузить файл {filename}: {e}")

    def create_tab(self, filename):
        tab_name = filename[:-5]
        self.notebook.add(tab_name)
        self.tab_modified[tab_name] = False

        # Создаем рамку для Treeview и Scrollbars
        container = ttk.Frame(self.notebook.tab(tab_name))
        container.pack(expand=True, fill='both', padx=5, pady=5)

        # Создаем Treeview
        tree = ttk.Treeview(container, selectmode='extended', show='tree')

        # Создаем Scrollbars
        vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)

        # Configure Treeview to use Scrollbars
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Place Treeview and Scrollbars in the frame
        tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')

        # Configure grid weights to make Treeview expandable
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        # Calculate minimum column width based on content
        default_font = tkfont.Font(family="TkDefaultFont", size=10)
        max_content_width = self.calculate_max_content_width(data=self.glossaries.get(filename, {}), tree=tree, font=default_font)
        tree.column("#0", minwidth=max_content_width)

        self.notebook.tab(tab_name).tree = tree
        self.update_tab_title(tab_name)
        self.display_glossary_data(tree)

        # Обновляем scrollregion canvas, чтобы scrollbars работали правильно
        tree.bind('<Configure>', lambda e: self.update_scroll_region(tree))

    def update_scroll_region(self, tree):
         tree.update_idletasks()
         tree.configure(scrollregion=tree.bbox("all"))

    def create_new_glossary(self):
        filename = simpledialog.askstring("Новый файл", "Введите имя нового файла (без расширения .json):")
        if filename:
            filename = filename + ".json"
            filepath = os.path.join(self.data_directory, filename)
            if os.path.exists(filepath):
                messagebox.showerror("Ошибка", "Файл с таким именем уже существует.")
                return

            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=4, ensure_ascii=False)
                self.glossaries[filename] = {}
                self.create_tab(filename)
                self.notebook.set(filename[:-5])
                self.notebook_tab_changed()
                self.is_modified = False
                messagebox.showinfo("Успех", "Файл создан.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать файл: {e}")

    def open_glossary(self):
        filepath = filedialog.askopenfilename(initialdir=self.data_directory, filetypes=[("JSON files", "*.json")])
        if filepath:
            filename = os.path.basename(filepath)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tab_name = filename[:-5]
                    if tab_name not in self.open_tabs:
                        self.glossaries[filename] = data
                        self.create_tab(filename)
                        self.open_tabs.add(tab_name)
                    else:
                        self.glossaries[filename] = data
                        self.display_glossary_data(self.notebook.tab(tab_name).tree)

                    self.notebook.set(tab_name)
                    self.notebook_tab_changed()
                    self.is_modified = False
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")

    def save_glossary_as(self):
        filepath = filedialog.asksaveasfilename(initialdir=self.data_directory, defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(self.glossaries[self.current_glossary], f, indent=4, ensure_ascii=False)

                new_filename = os.path.basename(filepath)
                old_filename = self.current_glossary
                self.glossaries[new_filename] = self.glossaries.pop(old_filename)
                self.current_glossary = new_filename

                current_tab = self.notebook.get()
                self.notebook.rename_tab(current_tab, new_filename[:-5])
                self.is_modified = False
                messagebox.showinfo("Успех", "Файл сохранен.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    def save_current_glossary(self, event=None):
        if self.current_glossary:
            filepath = os.path.join(self.data_directory, self.current_glossary)
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(self.glossaries[self.current_glossary], f, indent=4, ensure_ascii=False)
                self.is_modified = False
                tab_name = self.notebook.get()
                self.tab_modified[tab_name] = False
                self.update_tab_title(tab_name)
                messagebox.showinfo("Успех", "Файл сохранен.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    def notebook_tab_changed(self):
        selected_tab = self.notebook.get()
        if selected_tab:
            tree = self.notebook.tab(selected_tab).tree
            tab_text = selected_tab + ".json"
            if tab_text in self.glossaries:
                self.current_glossary = tab_text
                self.display_glossary_data(tree)
            else:
                self.current_glossary = None
                tree.delete(*tree.get_children())
                messagebox.showerror("Ошибка", "Файл не найден")
        else:
            self.current_glossary = None

    def display_glossary_data(self, tree):
        tree.delete(*tree.get_children())

        if self.current_glossary:
            data = self.glossaries[self.current_glossary]
            self.populate_tree(tree, "", data)

    def recursive_search(self, data, path="", filename=""):
        results = []
        search_term = self.search_entry.get()
        case_sensitive = self.search_case_sensitive.get()
        search_in_terms = self.search_in_terms.get()
        search_in_definitions = self.search_in_definitions.get()

        if not case_sensitive:
            search_term = search_term.lower()

        def search_in_string(text):
             if not isinstance(text, str):
                  return False
             text_lower = text.lower() if not case_sensitive else text
             return search_term in text_lower

        if isinstance(data, dict):
            for key, value in data.items():
                key_str = str(key)
                if not case_sensitive:
                    key_str = key_str.lower()
                if search_in_terms and search_in_string(key_str):
                    results.append((filename, f"{path}.{key}" if path else key, data[key]))

                if isinstance(value, (str, int, float, bool, type(None))):
                    value_str = str(value)
                    if search_in_definitions and search_in_string(value_str):
                        results.append((filename, f"{path}.{key}" if path else key, value))
                elif isinstance(value, (dict, list)):
                    results.extend(self.recursive_search(value, f"{path}.{key}" if path else key, filename))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (str, int, float, bool, type(None))):
                    item_str = str(item)
                    if search_in_definitions and search_in_string(item_str):
                        results.append((filename, f"{path}[{i}]" if path else f"[{i}]", item))
                elif isinstance(item, (dict, list)):
                    results.extend(self.recursive_search(item, f"{path}[{i}]" if path else f"[{i}]", filename))
        return results

    def search_term_all_files(self):
        self.search_results = []
        self.current_search_index = -1

        for filename, data in self.glossaries.items():
            results_for_file = self.recursive_search(data, filename=filename)
            self.search_results.extend(results_for_file)

        if self.search_results:
            self.current_search_index = 0
            self.show_search_results_window()
            self.update_search_result_display()
        else:
            messagebox.showinfo("Информация", "Совпадений не найдено.")

    def show_search_results_window(self):
        if self.search_results_window is None or not self.search_results_window.winfo_exists():
            self.search_results_window = ctk.CTkToplevel(self.root)
            self.search_results_window.title("Результаты поиска")
            self.search_results_window.geometry("600x400")
            self.search_results_window.protocol("WM_DELETE_WINDOW", self.close_search_results_window)

            self.search_result_text = ctk.CTkTextbox(self.search_results_window, wrap="word", font=ctk.CTkFont(size=14))
            self.search_result_text.pack(fill="both", expand=True, padx=10, pady=5)

            self.result_navigation_frame = ctk.CTkFrame(self.search_results_window)
            self.result_navigation_frame.pack(fill="x", padx=10, pady=5)

            self.prev_result_button = ctk.CTkButton(self.result_navigation_frame, text="<- Previous", command=self.show_previous_result, font=ctk.CTkFont(size=14))
            self.prev_result_button.pack(side="left", padx=5)

            self.result_index_label = ctk.CTkLabel(self.result_navigation_frame, text="", font=ctk.CTkFont(size=14))
            self.result_index_label.pack(side="left", padx=5)

            self.next_result_button = ctk.CTkButton(self.result_navigation_frame, text="Next ->", command=self.show_next_result, font=ctk.CTkFont(size=14))
            self.next_result_button.pack(side="left", padx=5)
            self.update_search_result_display()

    def close_search_results_window(self):
        if self.search_results_window:
            self.search_results_window.destroy()
            self.search_results_window = None
            self.search_result_text = None
            self.result_navigation_frame = None
            self.result_index_label = None
            self.next_result_button = None
            self.prev_result_button = None

    def update_search_result_display(self):
        if not self.search_results_window or not self.search_results:
            return

        self.search_result_text.configure(state="normal")
        self.search_result_text.delete("1.0", "end")

        if 0 <= self.current_search_index < len(self.search_results):
            filename, path, value = self.search_results[self.current_search_index]
            display_text = f"Файл: {filename}\n"
            if value is not None:
                display_text += f"Путь: {path}\nЗначение:\n"
                if isinstance(value, (dict, list)):
                    display_text += json.dumps(value, indent=4, ensure_ascii=False) + "\n"
                else:
                    display_text += str(value) + "\n"
            else:
                display_text += f"Ключ: {path.split('.')[-1] if '.' in path else path}\n"

            self.search_result_text.insert("1.0", display_text)
        self.search_result_text.configure(state="disabled")

        self.result_index_label.configure(text=f"Результат {self.current_search_index + 1} из {len(self.search_results)}")
        self.update_navigation_buttons()

    def update_navigation_buttons(self):
        if self.prev_result_button:
            self.prev_result_button.configure(state="normal" if self.current_search_index > 0 else "disabled")
        if self.next_result_button:
            self.next_result_button.configure(state="normal" if self.current_search_index < len(self.search_results) - 1 else "disabled")

    def show_next_result(self):
        if 0 <= self.current_search_index < len(self.search_results) - 1:
            self.current_search_index += 1
            self.update_search_result_display()

    def show_previous_result(self):
        if 0 < self.current_search_index < len(self.search_results):
            self.current_search_index -= 1
            self.update_search_result_display()

    def add_term(self):
        if not self.current_glossary:
            messagebox.showinfo("Информация", "Откройте файл для редактирования.")
            return

        def add_term_callback():
            term = term_entry.get()
            definition = definition_entry.get("1.0", "end").strip()

            if not term or not definition:
                messagebox.showerror("Ошибка", "Поля не могут быть пустыми.")
                return

            try:
                self.glossaries[self.current_glossary][term] = definition
            except json.JSONDecodeError:
                self.glossaries[self.current_glossary][term] = definition

            try:
                self.display_glossary_data(self.notebook.tab(self.notebook.get()).tree)
                self.save_current_glossary()
                add_term_window.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось добавить термин: {e}")

        add_term_window = ctk.CTkToplevel(self.root)
        add_term_window.title("Добавить термин")
        add_term_window.geometry("400x300")

        term_label = ctk.CTkLabel(add_term_window, text="Термин:", font=ctk.CTkFont(size=14))
        term_label.pack(pady=5)
        term_entry = ctk.CTkEntry(add_term_window, font=ctk.CTkFont(size=14))
        term_entry.pack(padx=10, pady=5, fill="x")

        definition_label = ctk.CTkLabel(add_term_window, text="Определение:", font=ctk.CTkFont(size=14))
        definition_label.pack(pady=5)
        definition_entry = ctk.CTkTextbox(add_term_window, wrap="word", height=8, font=ctk.CTkFont(size=14))
        definition_entry.pack(padx=10, pady=5, fill="both", expand=True)

        add_button = ctk.CTkButton(add_term_window, text="Добавить", command=add_term_callback, font=ctk.CTkFont(size=14))
        add_button.pack(pady=10)

    def edit_term(self):
        if not self.current_glossary:
            messagebox.showinfo("Информация", "Откройте файл для редактирования.")
            return

        def get_selected_item_path(tree):
            item = tree.selection()
            if not item:
                return None

            path = []
            current_item = item[0]
            while current_item:
                path.insert(0, tree.item(current_item, 'text'))
                current_item = tree.parent(current_item)
            return path

        def edit_term_callback():
            tree = self.notebook.tab(self.notebook.get()).tree
            path = get_selected_item_path(tree)

            if not path:
                messagebox.showinfo("Информация", "Выберите термин или определение для редактирования.")
                return

            def update_term_callback():
                new_value = definition_entry.get("1.0", "end").strip()

                if not new_value:
                    messagebox.showerror("Ошибка", "Значение не может быть пустым.")        
                    return

                try:

                    data = self.glossaries[self.current_glossary]
                    for key in path[:-1]:

                        if key.startswith("[") and key.endswith("]"):
                            index = int(key[1:-1])
                            data = data[index] 
                        else:
                            data = data[key] 


                    last_key = path[-1]  
                    if last_key.startswith("[") and last_key.endswith("]"):
                        index = int(last_key[1:-1])
                        data[index] = new_value 
                    else:
                        data[last_key] = new_value 

                    self.display_glossary_data(tree) 
                    self.save_current_glossary()
                    edit_term_window.destroy()
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось обновить термин: {e}")

            edit_term_window = ctk.CTkToplevel(self.root)
            edit_term_window.title(f"Редактировать {'/'.join(path)}")
            edit_term_window.geometry("400x300")

            definition_label = ctk.CTkLabel(edit_term_window, text="Значение:", font=ctk.CTkFont(size=14))
            definition_label.pack(pady=5)
            definition_entry = ctk.CTkTextbox(edit_term_window, wrap="word", height=8, font=ctk.CTkFont(size=14))


            try:
                data = self.glossaries[self.current_glossary]
                for key in path[:-1]:
                    if key.startswith("[") and key.endswith("]"):
                        index = int(key[1:-1])
                        data = data[index]
                    else:
                        data = data[key]

                last_key = path[-1]
                if last_key.startswith("[") and last_key.endswith("]"):
                    index = int(last_key[1:-1])
                    current_value = data[index]
                else:
                    current_value = data[last_key]
                definition_entry.insert("1.0", current_value)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось получить текущее значение: {e}")


            definition_entry.pack(padx=10, pady=5, fill="both", expand=True)

            update_button = ctk.CTkButton(edit_term_window, text="Обновить", command=update_term_callback, font=ctk.CTkFont(size=14))
            update_button.pack(pady=10)

        edit_term_callback()

    def delete_term(self):
        if not self.current_glossary:
            messagebox.showinfo("Информация", "Откройте файл для редактирования.")
            return

        def get_selected_item_path(tree):
            item = tree.selection()
            if not item:
                return None

            path = []
            current_item = item[0]
            while current_item:
                path.insert(0, tree.item(current_item, 'text'))
                current_item = tree.parent(current_item)
            return path

        def delete_term_callback():
            tree = self.notebook.tab(self.notebook.get()).tree
            path = get_selected_item_path(tree)

            if not path:
                messagebox.showinfo("Информация", "Выберите термин или определение для удаления.")
                return

            if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить '{'/'.join(path)}'?"):
                try:
                    data = self.glossaries[self.current_glossary]
                    for key in path[:-1]:

                        if key.startswith("[") and key.endswith("]"):
                            index = int(key[1:-1])
                            data = data[index]  
                        else:
                            data = data[key]


                    last_key = path[-1]
                    if last_key.startswith("[") and last_key.endswith("]"):
                        index = int(last_key[1:-1])
                        del data[index]
                    else:
                        del data[last_key]

                    self.display_glossary_data(tree)
                    self.save_current_glossary()
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось удалить: {e}")

        delete_term_callback() 
    def on_closing(self):
        for tab_name in self.open_tabs:
            if self.tab_modified.get(tab_name, False):
                self.notebook.set(tab_name)
                result = messagebox.askyesnocancel("Подтверждение", f"Файл '{tab_name}.json' был изменен. Сохранить изменения?")
                if result is True:
                    self.current_glossary = tab_name + ".json"
                    self.save_current_glossary()
                elif result is None:
                    return 
        self.root.destroy()

    def update_tab_title(self, tab_name):
        new_tab_name = f"{tab_name} *" if self.tab_modified.get(tab_name, False) else tab_name
        current_tab = self.notebook.get()

        try:
            tree = self.notebook.tab(tab_name).tree
            data = self.get_treeview_data(tree)

            self.notebook.delete(tab_name)
            self.notebook.add(new_tab_name)

            # Создаем рамку для Treeview и Scrollbars
            container = ttk.Frame(self.notebook.tab(new_tab_name))
            container.pack(expand=True, fill='both', padx=5, pady=5)

            # Создаем Treeview
            new_tree = ttk.Treeview(container, selectmode='extended', show='tree')

            # Создаем Scrollbars
            vsb = ttk.Scrollbar(container, orient="vertical", command=new_tree.yview)
            hsb = ttk.Scrollbar(container, orient="horizontal", command=new_tree.xview)

            # Configure Treeview to use Scrollbars
            new_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

            # Place Treeview and Scrollbars in the frame
            new_tree.grid(column=0, row=0, sticky='nsew')
            vsb.grid(column=1, row=0, sticky='ns')
            hsb.grid(column=0, row=1, sticky='ew')

            # Configure grid weights to make Treeview expandable
            container.grid_columnconfigure(0, weight=1)
            container.grid_rowconfigure(0, weight=1)

            # Calculate minimum column width based on content
            default_font = tkfont.Font(family="TkDefaultFont", size=10)
            max_content_width = self.calculate_max_content_width(data=self.convert_tree_data_to_dict(data), tree=new_tree, font=default_font)
            new_tree.column("#0", minwidth=max_content_width)

            self.notebook.tab(new_tab_name).tree = new_tree
            self.populate_tree_from_data(new_tree, "", data)

            if current_tab == tab_name:
                self.notebook.set(new_tab_name)

        except Exception as e:
            print(f"Error during tab update: {e}")
    
    def calculate_max_content_width(self, data, tree, font):
        max_width = 200
        for key, value in data.items():
            text_width = font.measure(str(key))
            max_width = max(max_width, text_width)
            if isinstance(value, dict):
                width = self.calculate_max_content_width(value, tree, font)
                max_width = max(max_width, width)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        width = self.calculate_max_content_width(item, tree, font)
                        max_width = max(max_width, width)
                    else:
                        text_width = font.measure(str(item))
                        max_width = max(max_width, text_width)
        return max_width

    def populate_tree(self, tree, parent, data):
        for key, value in data.items():
            node_id = tree.insert(parent, "end", text=key)
            if isinstance(value, dict):
                self.populate_tree(tree, node_id, value)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    child_id = tree.insert(node_id, "end", text=f"[{i}]")
                    if isinstance(item, dict) or isinstance(item, list):
                        self.populate_tree(tree, child_id, item)
                    else:
                        tree.insert(child_id, "end", text=item)
            else:
                tree.insert(node_id, "end", text=value)

    def get_treeview_data(self, tree):
        data = []
        for item in tree.get_children():
            data.append(self.get_treeview_item_data(tree, item))
        return data

    def get_treeview_item_data(self, tree, item):
        item_data = {"text": tree.item(item, "text")}
        children = tree.get_children(item)
        if children:
            item_data["children"] = [self.get_treeview_item_data(tree, child) for child in children]
        return item_data

    def populate_tree_from_data(self, tree, parent, data):
        for item_data in data:
            item_id = tree.insert(parent, "end", text=item_data["text"])
            if "children" in item_data:
                self.populate_tree_from_data(tree, item_id, item_data["children"])

    def convert_tree_data_to_dict(self, tree_data):
        result = {}
        for item in tree_data:
            text = item['text']
            children = item.get('children')
            if children:
                result[text] = self.convert_tree_data_to_dict(children)
            else:
                result[text] = ""  # или None, в зависимости от того, что вам нужно
        return result

    def on_text_changed(self, event):
        tab_name = self.notebook.get()
        if tab_name and not self.tab_modified.get(tab_name, False):
            self.tab_modified[tab_name] = True
            self.update_tab_title(tab_name)

if __name__ == "__main__":
    root = ctk.CTk()
    app = GlossaryApp(root)
    root.mainloop()