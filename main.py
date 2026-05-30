import sys
import os
import json
import sqlite3
from datetime import datetime
from urllib.parse import urlparse
from PySide6.QtCore import QUrl, QEvent, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QTabWidget,
    QLineEdit,
    QPushButton,
    QToolBar,
    QLabel,
    QStyle,
    QStatusBar,
    QMenu
)
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage


class WebBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simsovet - Neuro Handler")
        self.showMaximized()

        self.base_dir = os.path.dirname(__file__)
        self.data_dir = os.path.join(self.base_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)

        self.db_path = os.path.join(self.data_dir, "simsovet.db")
        self.init_db()

        icon_path = os.path.join(self.base_dir, "favicon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.profile = QWebEngineProfile("MyBrowserProfile", self)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        
        storage_path = os.path.join(self.data_dir, "browser_profile")
        self.profile.setPersistentStoragePath(storage_path)

        self.setStatusBar(QStatusBar(self))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(320)
        self.sidebar.setStyleSheet("background-color: #2e3440; color: #d8dee9; border-right: 1px solid #4c566a;")
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(5)
        for label, url in [("Alice", "https://alice.yandex.ru/?lang=ru"), ("Gemini", "https://gemini.google.com/?hl=ru"), ("DeepSeek", "https://chat.deepseek.com")]:
            btn = QPushButton(label)
            btn.setStyleSheet("padding: 8px; background-color: #3b4252; border: 1px solid #4c566a; border-radius: 4px; color: #eceff4; font-weight: bold; font-size: 10px;")
            btn.clicked.connect((lambda u, l: lambda: self.handle_quick_button(u, l))(url, label))
            btn_layout.addWidget(btn)
        sidebar_layout.addWidget(btn_container)

        btn_wonder = QWidget()
        btn_layout = QHBoxLayout(btn_wonder)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(5)
        btn_style = "padding: 8px; background-color: #3b4252; border: 1px solid #4c566a; border-radius: 4px; color: #eceff4; font-weight: bold; font-size: 10px;"
        get_post_btn = QPushButton("Day")
        get_post_btn.setStyleSheet(btn_style)
        get_post_btn.clicked.connect(self.handle_get_post)
        btn_layout.addWidget(get_post_btn)
        rewrite_day_btn = QPushButton("R")
        rewrite_day_btn.setStyleSheet(btn_style)
        rewrite_day_btn.clicked.connect(self.handle_rewrite_day)
        btn_layout.addWidget(rewrite_day_btn)
        get_week_btn = QPushButton("Week")
        get_week_btn.setStyleSheet(btn_style)
        get_week_btn.clicked.connect(self.handle_get_week)
        btn_layout.addWidget(get_week_btn)
        rewrite_week_btn = QPushButton("R")
        rewrite_week_btn.setStyleSheet(btn_style)
        rewrite_week_btn.clicked.connect(self.handle_rewrite_week)
        btn_layout.addWidget(rewrite_week_btn)
        get_month_btn = QPushButton("Month")
        get_month_btn.setStyleSheet(btn_style)
        get_month_btn.clicked.connect(self.handle_get_month)
        btn_layout.addWidget(get_month_btn)
        rewrite_month_btn = QPushButton("R")
        rewrite_month_btn.setStyleSheet(btn_style)
        rewrite_month_btn.clicked.connect(self.handle_rewrite_month)
        btn_layout.addWidget(rewrite_month_btn)
        sidebar_layout.addWidget(btn_wonder)

        self.recent_history_section = QWidget()
        recent_history_layout = QVBoxLayout(self.recent_history_section)
        recent_history_layout.setContentsMargins(0, 0, 0, 0)
        recent_history_layout.setSpacing(5)

        history_label = QLabel("Recent History")
        history_label.setStyleSheet("color: #eceff4; font-weight: bold; font-size: 11px; padding: 10px 10px 4px 10px;")
        recent_history_layout.addWidget(history_label)

        self.recent_history_layout = recent_history_layout

        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self.recent_history_section)

        self.db_status_label = QLabel()
        self.db_status_label.setStyleSheet("color: #81a1c1; font-size: 11px; padding: 10px; border-top: 1px solid #4c566a;")
        self.db_status_label.setWordWrap(True)
        sidebar_layout.addWidget(self.db_status_label)
        self.update_sidebar_status()

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        right_layout.addWidget(self.toolbar)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        self.tab_titles = {}
        self.tabs.tabBar().setMouseTracking(True)
        self.tabs.tabBar().installEventFilter(self)
        right_layout.addWidget(self.tabs)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(right_container)

        self.create_toolbar_actions()

        self.add_new_tab(QUrl("https://www.google.com/?hl=ru"), "New Tab")

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT NOT NULL,
                visited_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_feed (
                date TEXT PRIMARY KEY,
                text TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def log_to_history(self, title, url):
        if not url or url == "about:blank":
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO history (title, url, visited_at) VALUES (?, ?, ?)",
                (title, url, now)
            )
            conn.commit()
            conn.close()
            self.update_sidebar_status()
        except sqlite3.Error as e:
            print(f"Ошибка логирования в БД: {e}")

    def refresh_recent_history(self):
        while self.recent_history_layout.count():
            item = self.recent_history_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        history_label = QLabel("Recent History")
        history_label.setStyleSheet("color: #eceff4; font-weight: bold; font-size: 11px; padding: 10px 10px 4px 10px;")
        self.recent_history_layout.addWidget(history_label)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT title, url FROM history ORDER BY id DESC LIMIT 3")
            recent_rows = cursor.fetchall()
            conn.close()
        except sqlite3.Error:
            recent_rows = []

        for title, url in recent_rows:
            if not url:
                continue

            display_text = url
            if len(display_text) > 60:
                display_text = display_text[:57] + "..."

            btn = QPushButton(display_text)
            btn.setToolTip(url)
            btn.setStyleSheet("padding: 8px; background-color: #3b4252; border: 1px solid #4c566a; border-radius: 4px; color: #eceff4; font-size: 10px; text-align: left;")
            btn.clicked.connect(lambda checked=False, u=url, display_title=title: self.add_new_tab(QUrl(u), display_title or u))
            self.recent_history_layout.addWidget(btn)

        if not recent_rows:
            empty_label = QLabel("No history yet")
            empty_label.setStyleSheet("color: #d8dee9; font-size: 10px; padding: 0 10px 10px 10px;")
            self.recent_history_layout.addWidget(empty_label)

    def update_sidebar_status(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM history")
            total_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT url FROM history")
            urls = cursor.fetchall()
            domains = {urlparse(row[0]).netloc for row in urls if row[0]}
            unique_domains = len(domains)
            
            cursor.execute("SELECT visited_at FROM history ORDER BY id DESC LIMIT 1")
            last_time_row = cursor.fetchone()
            last_time = last_time_row[0].split(" ")[1] if last_time_row else "None"
            
            conn.close()
            
            status_text = f"Total: {total_count} | Domains: {unique_domains} | Last: {last_time}"
            self.db_status_label.setText(status_text)
            self.refresh_recent_history()
        except sqlite3.Error:
            self.db_status_label.setText("DB: Error loading statistics")

    def create_toolbar_actions(self):
        style = QApplication.style()

        self.back_btn = QPushButton()
        self.back_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.back_btn.clicked.connect(lambda: self.current_browser().back())
        self.toolbar.addWidget(self.back_btn)

        self.forward_btn = QPushButton()
        self.forward_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.forward_btn.clicked.connect(lambda: self.current_browser().forward())
        self.toolbar.addWidget(self.forward_btn)

        self.reload_btn = QPushButton()
        self.reload_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.reload_btn.clicked.connect(lambda: self.current_browser().reload())
        self.toolbar.addWidget(self.reload_btn)

        self.home_btn = QPushButton()
        self.home_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)) 
        self.home_btn.setText("Home")
        self.home_btn.clicked.connect(self.navigate_home)
        self.toolbar.addWidget(self.home_btn)

        self.toolbar.addSeparator()

        self.url_input = QLineEdit()
        self.url_input.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_input)

        self.go_btn = QPushButton("Go")
        self.go_btn.clicked.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.go_btn)

        self.toolbar.addSeparator()

        self.new_tab_btn = QPushButton("+ New Tab")
        self.new_tab_btn.clicked.connect(lambda: self.add_new_tab(QUrl("https://www.google.com/?hl=ru"), "New Tab"))
        self.toolbar.addWidget(self.new_tab_btn)

    def add_new_tab(self, qurl=None, title="New Tab"):
        browser = CustomWebEngineView(self)

        custom_page = CustomWebEnginePage(self, self.profile, browser)
        custom_page.linkHovered.connect(self.show_link_in_status_bar)
        browser.setPage(custom_page)

        if qurl:
            browser.setUrl(qurl)

        i = self.tabs.addTab(browser, title)
        self.tabs.setCurrentIndex(i)
        self.tab_titles[browser] = title

        # Handles address bar visual updates
        browser.urlChanged.connect(lambda qurl, b=browser: self.update_url_bar(qurl, b))

        # Dedicated handler to intercept background tabs / targets asynchronously
        browser.urlChanged.connect(lambda qurl, b=browser: self.handle_history_logging(qurl, b))

        browser.titleChanged.connect(lambda t, b=browser: self.update_tab_title(t, b))

        return browser

    def close_tab(self, index):
        if self.tabs.count() < 2:
            return
            
        browser = self.tabs.widget(index)
        if browser:
            self.tab_titles.pop(browser, None)
            browser.setPage(None) 
            browser.deleteLater()
            
        self.tabs.removeTab(index)

    def current_browser(self) -> QWebEngineView:
        return self.tabs.currentWidget()

    def navigate_home(self):
        if self.current_browser():
            self.current_browser().setUrl(QUrl("https://www.google.com/?hl=ru"))

    def navigate_to_url(self):
        q = QUrl(self.url_input.text())
        if q.scheme() == "":
            q.setScheme("http")
        
        if self.current_browser():
            self.current_browser().setUrl(q)

    def _feed_get_or_save(self, key):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT text FROM daily_feed WHERE date = ?", (key,))
            row = cursor.fetchone()
            if row:
                self.url_input.setText(row[0])
            else:
                text = self.url_input.text().strip()
                if text:
                    cursor.execute(
                        "INSERT OR REPLACE INTO daily_feed (date, text) VALUES (?, ?)",
                        (key, text)
                    )
                    conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"Feed DB error: {e}")

    def handle_get_post(self):
        key = datetime.now().strftime("%Y-%m-%d")
        self._feed_get_or_save(key)

    def handle_get_week(self):
        now = datetime.now()
        key = now.strftime("%Y-W%W")
        self._feed_get_or_save(key)

    def handle_get_month(self):
        key = datetime.now().strftime("%Y-%m")
        self._feed_get_or_save(key)

    def _feed_rewrite(self, key):
        text = self.url_input.text().strip()
        if not text:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO daily_feed (date, text) VALUES (?, ?)",
                (key, text)
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"Feed DB error: {e}")

    def handle_rewrite_day(self):
        self._feed_rewrite(datetime.now().strftime("%Y-%m-%d"))

    def handle_rewrite_week(self):
        self._feed_rewrite(datetime.now().strftime("%Y-W%W"))

    def handle_rewrite_month(self):
        self._feed_rewrite(datetime.now().strftime("%Y-%m"))

    def handle_quick_button(self, url, label):
        query_text = self.url_input.text().strip()
        if query_text and query_text != "https://www.google.com/?hl=ru":
            self._open_and_inject(url, label, query_text)
        else:
            self.add_new_tab(QUrl(url), label)

    def _open_and_inject(self, url, label, text):
        browser = self.add_new_tab(QUrl(url), label)
        injected = [False]
        target_domain = urlparse(url).netloc

        def do_inject(b):
            if injected[0]:
                return
            injected[0] = True
            js = f'''
            (function() {{
                const text = {json.dumps(text)};
                const enter = new KeyboardEvent('keydown', {{key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true, composed:true}});
                const enterUp = new KeyboardEvent('keyup', {{key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true, composed:true}});
                const inpEv = new InputEvent('input', {{bubbles:true}});

                let nativeSetter = null;
                try {{
                    nativeSetter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
                }} catch(e) {{}}

                const setValue = (el, val) => {{
                    if (nativeSetter) nativeSetter.call(el, val);
                    else el.value = val;
                }};

                const pressEnter = (el) => {{
                    setTimeout(() => {{
                        el.focus();
                        el.dispatchEvent(enter);
                        el.dispatchEvent(enterUp);
                    }}, 1000);
                }};

                const tryEl = (el, isCE) => {{
                    if (!el || el.offsetParent === null) return false;
                    el.focus();
                    if (isCE) el.innerText = text;
                    else setValue(el, text);
                    el.dispatchEvent(inpEv);
                    pressEnter(el);
                    return true;
                }};

                // rich-textarea shadow DOM (Gemini)
                const rt = document.querySelector('rich-textarea');
                if (rt && rt.shadowRoot) {{
                    const inner = rt.shadowRoot.querySelector('div[contenteditable="true"], [contenteditable]');
                    if (tryEl(inner, true)) return;
                }}

                // visible contenteditable divs
                for (const ed of document.querySelectorAll('div[contenteditable="true"]')) {{
                    if (tryEl(ed, true)) return;
                }}

                // visible textareas (last one = chat input at bottom)
                const tas = Array.from(document.querySelectorAll('textarea')).filter(t => t.offsetParent !== null);
                if (tas.length && tryEl(tas[tas.length - 1], false)) return;

                // visible text/search inputs
                const inps = Array.from(document.querySelectorAll('input[type="text"], input:not([type]), input[type="search"]')).filter(i => i.offsetParent !== null);
                if (inps.length) tryEl(inps[inps.length - 1], false);
            }})();
            '''
            b.page().runJavaScript(js)

        def on_load_ok(b=browser, inj=injected):
            if inj[0]:
                return
            url_str = b.url().toString()
            current_domain = urlparse(url_str).netloc
            if target_domain in current_domain:
                QTimer.singleShot(3000, lambda: do_inject(b))

        browser.loadFinished.connect(lambda ok: on_load_ok() if ok else None)

    def tab_changed(self, index):
        browser = self.tabs.widget(index)
        if browser:
            self.update_url_bar(browser.url(), browser)

    def update_url_bar(self, qurl, browser=None):
        if browser != self.current_browser():
            return
        
        url_str = qurl.toString()
        self.url_input.setText(url_str)
        self.back_btn.setEnabled(browser.history().canGoBack())
        self.forward_btn.setEnabled(browser.history().canGoForward())

    def handle_history_logging(self, qurl, browser):
        url_str = qurl.toString()
        if not url_str or url_str == "about:blank":
            return

        # Fetch structural/dynamic titles safely, default to domain if unavailable yet
        title = self.tab_titles.get(browser, "Loading...")
        if title in ["Loading...", "New Tab"] and browser.title():
            title = browser.title()
        elif title in ["Loading...", "New Tab"]:
            title = urlparse(url_str).netloc

        self.log_to_history(title, url_str)

    def update_tab_title(self, title, browser=None):
        index = self.tabs.indexOf(browser)
        if index != -1:
            self.tab_titles[browser] = title
            self.tabs.setTabToolTip(index, title)
            short_title = title[:15] + "..." if len(title) > 15 else title
            self.tabs.setTabText(index, short_title)

    def eventFilter(self, watched, event):
        if watched == self.tabs.tabBar():
            if event.type() == QEvent.Type.MouseMove:
                tab_index = self.tabs.tabBar().tabAt(event.position().toPoint())
                if tab_index != -1:
                    browser = self.tabs.widget(tab_index)
                    full_title = self.tab_titles.get(browser)
                    if full_title:
                        self.statusBar().showMessage(full_title)
                    else:
                        self.statusBar().clearMessage()
                else:
                    self.statusBar().clearMessage()
            elif event.type() == QEvent.Type.Leave:
                self.statusBar().clearMessage()

        return super().eventFilter(watched, event)

    def show_link_in_status_bar(self, link):
        if link:
            self.statusBar().showMessage(str(link))
        else:
            self.statusBar().clearMessage()

    def closeEvent(self, event):
        for i in reversed(range(self.tabs.count())):
            browser = self.tabs.widget(i)
            if browser:
                browser.setPage(None)
                browser.deleteLater()
        
        self.tabs.clear()
        QApplication.sendPostedEvents()
        QApplication.processEvents()
        event.accept()


class CustomWebEngineView(QWebEngineView):
    def __init__(self, browser_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.browser_window = browser_window

    def contextMenuEvent(self, event):
        page = self.page()
        selected_text = page.selectedText()

        menu = QMenu(self)

        back_action = menu.addAction("Back")
        back_action.setEnabled(self.history().canGoBack())
        back_action.triggered.connect(self.back)

        forward_action = menu.addAction("Forward")
        forward_action.setEnabled(self.history().canGoForward())
        forward_action.triggered.connect(self.forward)

        reload_action = menu.addAction("Reload")
        reload_action.triggered.connect(self.reload)

        menu.addSeparator()

        copy_action = menu.addAction("Copy")
        copy_action.setEnabled(bool(selected_text))
        copy_action.triggered.connect(lambda: page.triggerAction(QWebEnginePage.WebAction.Copy))

        select_all_action = menu.addAction("Select All")
        select_all_action.triggered.connect(lambda: page.triggerAction(QWebEnginePage.WebAction.SelectAll))

        menu.addSeparator()

        copy_url_action = menu.addAction("Copy selected to URL input")
        copy_url_action.setEnabled(bool(selected_text))
        copy_url_action.triggered.connect(lambda: self.browser_window.url_input.setText(selected_text))

        menu.exec(self.mapToGlobal(event.pos()))


class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, browser_window, profile, *args, **kwargs):
        super().__init__(profile, *args, **kwargs)
        self.browser_window = browser_window

    def createWindow(self, _type):
        new_browser = self.browser_window.add_new_tab(qurl=None, title="Loading...")
        return new_browser.page()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    if sys.platform == "win32":
        import ctypes
        myappid = "simsovet.neurohandler.browser.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    window = WebBrowser()
    window.show()
    sys.exit(app.exec())