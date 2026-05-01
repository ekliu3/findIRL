from __future__ import annotations

from typing import Iterator, Optional

from fastapi import (Depends, FastAPI, Form, HTTPException, Query, Request,
                     status)
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from models import models, schemas
from sqlmodel import Session, SQLModel, create_engine, select

DATABASE_URL = "postgresql+psycopg://app:app@dev_pg:5432/db"
engine = create_engine(DATABASE_URL, echo=False)
SQLModel.metadata.create_all(engine)

# Dependency to get a database session


def get_session():
    with Session(engine) as session:
        yield session


app = FastAPI()

# Templates directory
templates = Jinja2Templates(directory="templates")
# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main page"""
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/posts", response_class=HTMLResponse)
def posts_page(request: Request):
    return templates.TemplateResponse("posts.html", {"request": request})


def get_user_or_404(session: Session, user_id: int) -> models.User:
    user = session.get(models.User, user_id)
    if not user:
        raise HTTPException(
            status_code=404, detail=f"User {user_id} not found")
    return user


def get_post_or_404(session: Session, post_id: int) -> models.Post:
    post = session.get(models.Post, post_id)
    if not post:
        raise HTTPException(
            status_code=404, detail=f"Post {post_id} not found")
    return post


def get_comment_or_404(session: Session, comment_id: int) -> models.Comment:
    comment = session.get(models.Comment, comment_id)
    if not comment:
        raise HTTPException(
            status_code=404, detail=f"Comment {comment_id} not found")
    return comment


@app.post("/api/users", response_model=schemas.UserOut, status_code=201)
def create_user(user: schemas.UserIn, session: Session = Depends(get_session)):
    out = models.User(
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        password=user.password
    )
    session.add(out)
    session.commit()
    session.refresh(out)
    return out


@app.get("/api/users", response_model=list[schemas.UserOut])
def list_users(session: Session = Depends(get_session)):
    stmt = select(models.User)
    return session.exec(stmt).all()


@app.post("/api/posts", response_model=schemas.PostOut, status_code=201)
def create_post(
    post: schemas.PostIn,
    session: Session = Depends(get_session),
):
    get_user_or_404(session, post.user_id)

    out = models.Post(
        title=post.title,
        text=post.text,
        duration=post.duration,
        user_id=post.user_id,
    )
    session.add(out)
    session.commit()
    session.refresh(out)
    return out


@app.get("/api/posts", response_model=list[schemas.PostOut])
def list_posts(session: Session = Depends(get_session)):
    stmt = select(models.Post)
    return session.exec(stmt).all()


@app.delete("/api/posts/{post_id}", status_code=204)
def delete_post(
    post_id: int,
    session: Session = Depends(get_session),
):
    post = get_post_or_404(session, post_id)
    session.delete(post)
    session.commit()
    return Response(status_code=204)


@app.post("/api/comments", response_model=schemas.CommentOut, status_code=201)
def create_comment(
    comment: schemas.CommentIn,
    session: Session = Depends(get_session),
):
    get_user_or_404(session, comment.user_id)
    get_post_or_404(session, comment.post_id)

    out = models.Comment(
        comment=comment.comment,
        user_id=comment.user_id,
        post_id=comment.post_id,
    )
    session.add(out)
    session.commit()
    session.refresh(out)
    return out


@app.get("/api/posts/{post_id}/comments", response_model=list[schemas.CommentOut])
def list_comments_for_post(
    post_id: int,
    session: Session = Depends(get_session),
):
    get_post_or_404(session, post_id)
    stmt = select(models.Comment).where(models.Comment.post_id == post_id)
    return session.exec(stmt).all()


@app.get("/fragments/posts/new", response_class=HTMLResponse)
def new_post_fragment(
    request: Request,
    session: Session = Depends(get_session),
):
    users = session.exec(select(models.User)).all()

    return templates.TemplateResponse(
        "fragments/new_post.html",
        {
            "request": request,
            "users": users,
        },
    )


@app.get("/fragments/posts/list", response_class=HTMLResponse)
def posts_list_fragment(
    request: Request,
    session: Session = Depends(get_session),
):
    posts = session.exec(select(models.Post)).all()
    users = session.exec(select(models.User)).all()

    return templates.TemplateResponse(
        "fragments/posts_list.html",
        {
            "request": request,
            "posts": posts,
            "users": users,
        },
    )


@app.get("/fragments/posts/{post_id}", response_class=HTMLResponse)
def post_row_fragment(
    post_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    post = get_post_or_404(session, post_id)

    return templates.TemplateResponse(
        "fragments/post_row.html",
        {
            "request": request,
            "post": post,
        },
    )


@app.post("/fragments/posts", response_class=HTMLResponse)
def create_post_fragment(
    request: Request,
    title: str = Form(...),
    text: str = Form(...),
    duration: int = Form(...),
    user_id: int = Form(...),
    session: Session = Depends(get_session),
):
    get_user_or_404(session, user_id)

    post = models.Post(
        title=title,
        text=text,
        duration=duration,
        user_id=user_id,
    )
    session.add(post)
    session.commit()
    session.refresh(post)

    return templates.TemplateResponse(
        "fragments/post_row.html",
        {
            "request": request,
            "post": post,
        },
    )


@app.delete("/fragments/posts/{post_id}", response_class=HTMLResponse)
def delete_post_fragment(
    post_id: int,
    session: Session = Depends(get_session),
):
    post = get_post_or_404(session, post_id)
    session.delete(post)
    session.commit()
    return HTMLResponse("")


@app.get("/fragments/posts/{post_id}/edit", response_class=HTMLResponse)
def edit_post_fragment(
    post_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    post = get_post_or_404(session, post_id)

    return templates.TemplateResponse(
        "fragments/post_edit.html",
        {
            "request": request,
            "post": post,
        },
    )


@app.put("/fragments/posts/{post_id}", response_class=HTMLResponse)
def update_post(
    post_id: int,
    title: str = Form(...),
    text: str = Form(...),
    duration: int = Form(...),
    request: Request = None,
    session: Session = Depends(get_session),
):
    post = get_post_or_404(session, post_id)

    post.title = title
    post.text = text
    post.duration = duration

    session.commit()
    session.refresh(post)

    return templates.TemplateResponse(
        "fragments/post_row.html",
        {
            "request": request,
            "post": post,
        },
    )


@app.get("/fragments/posts/{post_id}/comments", response_class=HTMLResponse)
def comments_fragment(
    post_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    get_post_or_404(session, post_id)
    comments = session.exec(
        select(models.Comment).where(models.Comment.post_id == post_id)
    ).all()

    users = session.exec(select(models.User)).all()

    return templates.TemplateResponse(
        "fragments/comments_list.html",
        {
            "request": request,
            "post_id": post_id,
            "comments": comments,
            "users": users,
        },
    )


@app.post("/fragments/posts/{post_id}/comments", response_class=HTMLResponse)
def create_comment(
    post_id: int,
    request: Request,
    text: str = Form(...),
    user_id: int = Form(...),
    session: Session = Depends(get_session),
):
    get_post_or_404(session, post_id)
    get_user_or_404(session, user_id)

    out = models.Comment(
        text=text,
        user_id=user_id,
        post_id=post_id,
    )

    session.add(out)
    session.commit()
    session.refresh(out)

    return templates.TemplateResponse(
        "fragments/comment_row.html",
        {
            "request": request,
            "comment": out,
        },
    )
