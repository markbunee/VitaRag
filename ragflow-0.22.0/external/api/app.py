import os
import sys

_base_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_base_dir, "..", ".."))
_langchain_graph = os.path.join(_project_root, "external", "langchain-graph")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _langchain_graph not in sys.path:
    sys.path.insert(0, _langchain_graph)
#
#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

# from beartype import BeartypeConf
# from beartype.claw import beartype_all  # <-- you didn't sign up for this
# beartype_all(conf=BeartypeConf(violation_type=UserWarning))    # <-- emit warnings from all code

from common.log_utils import init_root_logger

init_root_logger("ragflow_server")

import logging
import os
import signal
import sys
import time
import traceback
import threading

from werkzeug.serving import run_simple
from external.api.apps import app
# from dotenv import load_dotenv
# load_dotenv()
# app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

from api.db.runtime_config import RuntimeConfig
from common import settings
from rag.utils.mcp_tool_call_conn import shutdown_all_mcp_sessions

stop_event = threading.Event()

# RAGFLOW_DEBUGPY_LISTEN = int(os.environ.get('RAGFLOW_DEBUGPY_LISTEN', "0"))

# def update_progress():
#     lock_value = str(uuid.uuid4())
#     redis_lock = RedisDistributedLock("update_progress", lock_value=lock_value, timeout=60)
#     logging.info(f"update_progress lock_value: {lock_value}")
#     while not stop_event.is_set():
#         try:
#             if redis_lock.acquire():
#                 DocumentService.update_progress()
#                 redis_lock.release()
#         except Exception:
#             logging.exception("update_progress exception")
#         finally:
#             try:
#                 redis_lock.release()
#             except Exception:
#                 logging.exception("update_progress exception")
#             stop_event.wait(6)


def signal_handler(sig, frame):
    logging.info("Received interrupt signal, shutting down...")
    shutdown_all_mcp_sessions()
    stop_event.set()
    time.sleep(1)
    sys.exit(0)


if __name__ == "__main__":
    # logging.info(r"""
    #     ____   ___    ______ ______ __
    #    / __ \ /   |  / ____// ____// /____  _      __
    #   / /_/ // /| | / / __ / /_   / // __ \| | /| / /
    #  / _, _// ___ |/ /_/ // __/  / // /_/ /| |/ |/ /
    # /_/ |_|/_/  |_|\____//_/    /_/ \____/ |__/|__/

    # """)
    # logging.info(
    #     f'RAGFlow version: {get_ragflow_version()}'
    # )
    # logging.info(
    #     f'project base: {get_project_base_directory()}'
    # )
    # show_configs()
    settings.init_settings()
    settings.print_rag_settings()

    # if RAGFLOW_DEBUGPY_LISTEN > 0:
    #     logging.info(f"debugpy listen on {RAGFLOW_DEBUGPY_LISTEN}")
    #     import debugpy
    #     debugpy.listen(("0.0.0.0", RAGFLOW_DEBUGPY_LISTEN))

    # init db
    # init_web_db()
    # init_web_data()
    # init runtime config
    # import argparse

    # parser = argparse.ArgumentParser()
    # parser.add_argument(
    #     "--version", default=False, help="RAGFlow version", action="store_true"
    # )
    # parser.add_argument(
    #     "--debug", default=False, help="debug mode", action="store_true"
    # )
    # args = parser.parse_args()
    # if args.version:
    #     print(get_ragflow_version())
    #     sys.exit(0)

    # RuntimeConfig.DEBUG = args.debug
    # if RuntimeConfig.DEBUG:
    #     logging.info("run on debug mode")

    # RuntimeConfig.init_env()
    # RuntimeConfig.init_config(JOB_SERVER_HOST=settings.HOST_IP, HTTP_PORT=settings.HOST_PORT)

    # GlobalPluginManager.load_plugins()

    # signal.signal(signal.SIGINT, signal_handler)
    # signal.signal(signal.SIGTERM, signal_handler)

    # def delayed_start_update_progress():
    #     logging.info("Starting update_progress thread (delayed)")
    #     t = threading.Thread(target=update_progress, daemon=True)
    #     t.start()

    # if RuntimeConfig.DEBUG:
    #     if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    #         threading.Timer(1.0, delayed_start_update_progress).start()
    # else:
    #     threading.Timer(1.0, delayed_start_update_progress).start()

    # init smtp server
    # if settings.SMTP_CONF:
    #     app.config["MAIL_SERVER"] = settings.MAIL_SERVER
    #     app.config["MAIL_PORT"] = settings.MAIL_PORT
    #     app.config["MAIL_USE_SSL"] = settings.MAIL_USE_SSL
    #     app.config["MAIL_USE_TLS"] = settings.MAIL_USE_TLS
    #     app.config["MAIL_USERNAME"] = settings.MAIL_USERNAME
    #     app.config["MAIL_PASSWORD"] = settings.MAIL_PASSWORD
    #     app.config["MAIL_DEFAULT_SENDER"] = settings.MAIL_DEFAULT_SENDER
    #     smtp_mail_server.init_app(app)

    # start http server
    try:
        logging.info("RAGFlow HTTP server start...")
        run_simple(
            hostname=settings.HOST_IP,
            port=8009,
            application=app,
            threaded=True,
            use_reloader=RuntimeConfig.DEBUG,
            use_debugger=RuntimeConfig.DEBUG,
        )
    except Exception:
        traceback.print_exc()
        stop_event.set()
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGKILL)
