from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .blogger import BloggerClient
from .config import Settings
from .fetcher import ArticleFetcher
from .formatter import render_markdown
from .service import ProcessResult, PublishingService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="news2blogger",
        description="Summarize, translate, credit, and publish articles to Blogger.",
    )
    parser.add_argument("--env-file", default=".env", help="Environment file (default: .env)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    url_parser = subparsers.add_parser("url", help="Process one article URL")
    url_parser.add_argument("url")
    _add_publish_options(url_parser)
    url_parser.add_argument(
        "--output",
        type=Path,
        help="Save a dry-run preview or reuse an existing preview with --publish",
    )

    feed_parser = subparsers.add_parser("feed", help="Process recent URLs from an RSS feed")
    feed_parser.add_argument("feed_url")
    feed_parser.add_argument("--limit", type=int, default=10)
    _add_publish_options(feed_parser)

    subparsers.add_parser("list-blogs", help="List Blogger blogs available to your account")
    return parser


def _add_publish_options(parser: argparse.ArgumentParser) -> None:
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Generate HTML without Blogger")
    mode.add_argument("--publish", action="store_true", help="Publish immediately, not as draft")
    parser.add_argument("--force", action="store_true", help="Process a duplicate URL again")


def _show_result(result: ProcessResult, output: Path | None = None) -> None:
    if result.skipped:
        print("Skipped: this source URL was already processed.")
        return
    print(f"Title: {result.post.title}")
    if result.blogger_post_id:
        print(f"Blogger post ID: {result.blogger_post_id}")
    elif output:
        preview = render_markdown(result.article, result.post)
        output.write_text(preview, encoding="utf-8")
        print(f"Saved Markdown preview: {output}")
    else:
        print("\nGenerated HTML:\n")
        print(result.html)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "output", None) and not (args.dry_run or args.publish):
        parser.error("--output requires --dry-run or --publish")
    settings = Settings.from_env(args.env_file)
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        if args.command == "list-blogs":
            client = BloggerClient(settings.blogger_client_secrets, settings.blogger_token_file)
            for blog in client.list_blogs():
                print(f"{blog.get('id')}\t{blog.get('name')}\t{blog.get('url')}")
            return 0

        service = PublishingService(settings)
        if args.command == "url":
            if args.output and args.publish:
                if not args.output.is_file():
                    parser.error(
                        f"Markdown preview not found: {args.output}. "
                        "Generate it first with --dry-run --output."
                    )
                _show_result(
                    service.publish_markdown(args.url, args.output, force=args.force)
                )
                return 0
            _show_result(
                service.process_url(
                    args.url,
                    dry_run=args.dry_run,
                    force=args.force,
                    publish=True if args.publish else None,
                ),
                args.output,
            )
            return 0


        fetcher = ArticleFetcher(settings.http_user_agent)
        failures = 0
        for url in fetcher.feed_urls(args.feed_url, limit=args.limit):
            try:
                _show_result(
                    service.process_url(
                        url,
                        dry_run=args.dry_run,
                        force=args.force,
                        publish=True if args.publish else None,
                    )
                )
            except Exception:
                failures += 1
                logging.exception("Failed to process %s", url)
        return 1 if failures else 0
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        logging.error("%s", exc)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
