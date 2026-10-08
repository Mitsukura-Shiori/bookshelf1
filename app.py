import sqlite3
from datetime import date
from pathlib import Path
import pandas as pd
import streamlit as st

# データベースファイルのパス設定
DB_PATH = Path(__file__).parent / "bookshelf.db"


def get_connection():
    """SQLite データベース接続を取得"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """データベースおよびテーブルの初期化"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT,
                published_date TEXT,
                rating INTEGER DEFAULT 3,
                memo TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def insert_book(title: str, author: str, genre: str, published_date: str, rating: int, memo: str):
    """新しい書籍を登録"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO books (title, author, genre, published_date, rating, memo)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, author, genre, published_date, rating, memo),
        )
        conn.commit()


def fetch_books(search_query: str = "", filter_genre: str = "すべて"):
    """書籍データを取得（検索・絞り込み対応）"""
    with get_connection() as conn:
        query = "SELECT id, title, author, genre, published_date, rating, memo, created_at FROM books WHERE 1=1"
        params = []

        if search_query:
            query += " AND (title LIKE ? OR author LIKE ?)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])

        if filter_genre and filter_genre != "すべて":
            query += " AND genre = ?"
            params.append(filter_genre)

        query += " ORDER BY id DESC"
        df = pd.read_sql_query(query, conn, params=params)
        return df


def delete_book(book_id: int):
    """書籍を削除"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()


def get_book_by_id(book_id: int):
    """指定IDの書籍データを1件取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_book(book_id: int, title: str, author: str, genre: str, published_date: str, rating: int, memo: str):
    """書籍情報を更新"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE books
            SET title = ?, author = ?, genre = ?, published_date = ?, rating = ?, memo = ?
            WHERE id = ?
            """,
            (title, author, genre, published_date, rating, memo, book_id),
        )
        conn.commit()


# アプリケーション初期設定
st.set_page_config(
    page_title="書籍管理システム",
    page_icon="📚",
    layout="wide",
)

# DB初期化
init_db()

st.title("📚 書籍管理システム")
st.caption("SQLite3 を利用した書籍データの登録および一覧表示アプリ")

# ジャンル候補
GENRES = ["文学・小説", "ビジネス・経済", "IT・技術書", "自然科学・工学", "趣味・実用", "コミック・雑誌", "その他"]

# タブ切り替え: 書籍一覧、新規登録、編集
tab_list, tab_add, tab_edit = st.tabs(["📋 書籍データ一覧", "➕ 書籍の新規登録", "✏️ 書籍の編集"])

# ---------------- 書籍一覧タブ ----------------
with tab_list:
    st.subheader("登録済み書籍一覧")

    # 検索・フィルターUI
    col_search, col_filter = st.columns([3, 2])
    with col_search:
        search_query = st.text_input("🔍 タイトル・著者で検索", placeholder="キーワードを入力...")
    with col_filter:
        filter_genre = st.selectbox("🏷️ ジャンルで絞り込み", options=["すべて"] + GENRES)

    # データ取得
    df_books = fetch_books(search_query=search_query, filter_genre=filter_genre)

    st.write(f"該当件数: **{len(df_books)}** 件")

    if df_books.empty:
        st.info("登録されている書籍データがありません。「書籍の新規登録」タブから書籍を追加してください。")
    else:
        # 表示用の列名マッピングと評価の星表示変換
        display_df = df_books.copy()
        display_df["評価"] = display_df["rating"].apply(lambda r: "★" * int(r) + "☆" * (5 - int(r)) if pd.notnull(r) else "")

        # 表示用カラムの整理
        display_df = display_df.rename(
            columns={
                "id": "ID",
                "title": "書籍タイトル",
                "author": "著者",
                "genre": "ジャンル",
                "published_date": "出版日/購入日",
                "memo": "メモ",
                "created_at": "登録日時",
            }
        )

        columns_order = ["ID", "書籍タイトル", "著者", "ジャンル", "出版日/購入日", "評価", "メモ", "登録日時"]
        st.dataframe(
            display_df[columns_order],
            use_container_width=True,
            hide_index=True,
        )

        # 書籍の個別削除機能
        with st.expander("🗑️ 書籍の削除"):
            delete_id = st.number_input(
                "削除したい書籍のIDを入力してください",
                min_value=1,
                step=1,
            )
            if st.button("指定IDの書籍を削除", type="secondary"):
                if delete_id in df_books["id"].values:
                    delete_book(delete_id)
                    st.success(f"ID: {delete_id} の書籍を削除しました。")
                    st.rerun()
                else:
                    st.error("指定されたIDの書籍は見つかりませんでした。")

# ---------------- 書籍登録タブ ----------------
with tab_add:
    st.subheader("書籍情報の登録")
    st.write("以下のフォームに書籍情報を入力して「登録」ボタンを押してください。")

    with st.form("book_register_form", clear_on_submit=True):
        col_title, col_author = st.columns(2)
        with col_title:
            title = st.text_input("書籍タイトル *", placeholder="例: ゼロから作るDeep Learning")
        with col_author:
            author = st.text_input("著者名 *", placeholder="例: 斎藤 康毅")

        col_genre, col_date = st.columns(2)
        with col_genre:
            genre = st.selectbox("ジャンル", options=GENRES)
        with col_date:
            published_date = st.date_input("出版日 / 購入日", value=date.today())

        rating = st.slider("評価", min_value=1, max_value=5, value=3, format="%d 星")
        memo = st.text_area("メモ・感想", placeholder="読んだ感想や要点を入力できます（任意）")

        submitted = st.form_submit_button("登録する", type="primary", use_container_width=True)

        if submitted:
            # 入力チェック
            if not title.strip():
                st.error("書籍タイトルを入力してください。")
            elif not author.strip():
                st.error("著者名を入力してください。")
            else:
                insert_book(
                    title=title.strip(),
                    author=author.strip(),
                    genre=genre,
                    published_date=str(published_date),
                    rating=rating,
                    memo=memo.strip(),
                )
                st.success(f"『{title.strip()}』を登録しました！「書籍データ一覧」タブで確認できます。")

# ---------------- 書籍編集タブ ----------------
with tab_edit:
    st.subheader("書籍情報の編集")
    all_books = fetch_books()

    if all_books.empty:
        st.info("編集可能な書籍がありません。まずは「書籍の新規登録」タブから書籍を追加してください。")
    else:
        book_options = {
            int(row["id"]): f"ID {row['id']}: {row['title']}（著者: {row['author']}）"
            for _, row in all_books.iterrows()
        }

        selected_id = st.selectbox(
            "編集する書籍を選択してください",
            options=list(book_options.keys()),
            format_func=lambda x: book_options[x],
        )

        target_book = get_book_by_id(selected_id)

        if target_book:
            # 日付のパース
            try:
                parsed_date = date.fromisoformat(target_book["published_date"])
            except Exception:
                parsed_date = date.today()

            genre_index = GENRES.index(target_book["genre"]) if target_book["genre"] in GENRES else 0

            with st.form(f"edit_form_{selected_id}"):
                col_t, col_a = st.columns(2)
                with col_t:
                    edit_title = st.text_input("書籍タイトル *", value=target_book["title"])
                with col_a:
                    edit_author = st.text_input("著者名 *", value=target_book["author"])

                col_g, col_d = st.columns(2)
                with col_g:
                    edit_genre = st.selectbox("ジャンル", options=GENRES, index=genre_index)
                with col_d:
                    edit_date = st.date_input("出版日 / 購入日", value=parsed_date)

                current_rating = int(target_book["rating"]) if target_book["rating"] is not None else 3
                edit_rating = st.slider(
                    "評価",
                    min_value=1,
                    max_value=5,
                    value=max(1, min(5, current_rating)),
                    format="%d 星",
                )
                edit_memo = st.text_area("メモ・感想", value=target_book["memo"] or "")

                update_submitted = st.form_submit_button("更新を保存する", type="primary", use_container_width=True)

                if update_submitted:
                    if not edit_title.strip():
                        st.error("書籍タイトルを入力してください。")
                    elif not edit_author.strip():
                        st.error("著者名を入力してください。")
                    else:
                        update_book(
                            book_id=selected_id,
                            title=edit_title.strip(),
                            author=edit_author.strip(),
                            genre=edit_genre,
                            published_date=str(edit_date),
                            rating=edit_rating,
                            memo=edit_memo.strip(),
                        )
                        st.success(f"ID: {selected_id}『{edit_title.strip()}』の情報を更新しました！")
                        st.rerun()
