"""`citationer serve` — 启动本地 Web 仪表板。"""

from __future__ import annotations

import typer

app = typer.Typer(
    name="serve",
    help="启动本地 Web 仪表板。",
    invoke_without_command=True,
    no_args_is_help=False,
)


@app.callback()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="绑定主机"),
    port: int = typer.Option(8000, "--port", help="绑定端口"),
    reload: bool = typer.Option(False, "--reload", help="开发模式：自动重载"),
) -> None:
    """运行 Citationer Web 服务器。"""
    try:
        import uvicorn

        from citationer.web.app import create_app
    except ImportError as exc:
        typer.echo(
            "Web 服务器依赖未安装。请运行：pip install 'citationer[web]'",
            err=True,
        )
        raise typer.Exit(code=1) from exc

    uvicorn.run(
        create_app,
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


if __name__ == "__main__":
    app()
