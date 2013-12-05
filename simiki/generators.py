#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Convert Markdown file to html, which is embeded in html template.
"""

from __future__ import print_function, with_statement, unicode_literals

import os
import sys
import codecs
import datetime
from os import path as osp
from pprint import pprint

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader

from simiki import configs
from simiki import utils

class BaseGenerator(object):
    def __init__(self):
        self.env = Environment(loader = FileSystemLoader(configs.TPL_PATH))
        self.site_settings = {
            "name" : configs.WIKI_NAME,
            "keywords" : configs.WIKI_KEYWORDS,
            "description" : configs.WIKI_DESCRIPTION,
            "url" : configs.DOMAIN,
            "theme" : configs.THEME,
            "author" : configs.AUTHOR,
            "author_email" : configs.AUTHOR_EMAIL,
        }

    def get_catalog_and_mdown(self, mdown_file):
        """Get the catalog's and markdown's(with extension) name."""
        # @todo, if path with `/`?
        split_path = mdown_file.split("/")
        mdown, catalog = split_path[-1], split_path[-2]

        return (catalog, mdown)

    def get_meta_and_content(self, mdown_file):
        """Split the markdown file texts by triple-dashed lines.

        The content in the middle of triple-dashed lines is meta datas, which 
            use Yaml format.
        The other content is the markdown texts.
        """
        with codecs.open(mdown_file, "rb", "utf-8") as fd:
            text_lists = fd.readlines()

        meta_notation = "---\n"
        if text_lists[0] != meta_notation:
            sys.exit(utils.color_msg(
                "error", "First line must be triple-dashed!"))

        meta_lists = []
        meta_end_flag = False
        idx = 1
        while not meta_end_flag:
            meta_lists.append(text_lists[idx])
            idx += 1
            if text_lists[idx] == meta_notation:
                meta_end_flag = True
        content_lists = text_lists[idx+1:]
        meta_yaml = "".join(meta_lists)
        contents = "".join(content_lists)
        return (meta_yaml, contents)

    def get_meta_datas(self, meta_yaml):
        """Get meta datas and validate them

        :param meta_yaml: Meta info in yaml format
        """
        meta_datas = yaml.load(meta_yaml)
        for m in ("title", "date"):
            if m not in meta_datas:
                sys.exit(utils.color_msg("error", "No '%s' in meta data!" % m))
        return meta_datas

class PageGenerator(BaseGenerator):

    def __init__(self, mdown_file):
        """
        :param mdown_file: The path of markdown file
        """
        super(PageGenerator, self).__init__()
        self.mdown_file = osp.realpath(mdown_file)

    def parse_mdown(self, contents):
        """Parse markdown text to html.

        :param contents: Markdown text lists
        """
        body_content = markdown.markdown(contents, \
            extensions=["fenced_code", "codehilite(guess_lang=False)"])

        return body_content

    def get_tpl_vars(self):
        catalog, _ = self.get_catalog_and_mdown(self.mdown_file)
        meta_yaml, contents = self.get_meta_and_content(self.mdown_file)
        meta_datas = self.get_meta_datas(meta_yaml)
        title = meta_datas["title"]
        body_content = self.parse_mdown(contents)
        tpl_vars = {
            "site" : self.site_settings,
            "title" : title,
            "content" : body_content,
            "catalog" : catalog,
        }

        return tpl_vars

    def mdown2html(self):
        """Load template, and generate html.

        XXX: The post template must named `post.html`
        """

        tpl_vars = self.get_tpl_vars()
        html = self.env.get_template("post.html").render(tpl_vars)

        return html

    def output_to_file(self, html):
        """Write generated html to file"""
        catalog, mdown = self.get_catalog_and_mdown(self.mdown_file)
        output_catalog_path = osp.join(configs.OUTPUT_PATH, catalog)
        if not utils.check_path_exists(output_catalog_path):
            print(utils.color_msg(
                "info", 
                "The output catalog %s not exists, create it" \
                % output_catalog_path)
            )
            os.mkdir(output_catalog_path)
        mdown_name = osp.splitext(mdown)[0]
        output_file = osp.join(output_catalog_path, mdown_name+".html")
        with codecs.open(output_file, "wb", "utf-8") as fd:
            fd.write(html)

class CatalogGenerator(BaseGenerator):

    def __init__(self, root_path, content_path, output_path):
        super(CatalogGenerator, self).__init__()
        self.root_path = root_path
        self.content_path = content_path
        self.output_path = output_path

    def get_tpl_vars(self):
        """
        XXX: Only for one level dir.
        """
        catalog_page_list = {}

        sub_dirs = [ _ for _ in os.listdir(self.content_path)]
        for sub_dir in sub_dirs:
            abs_sub_dir = osp.join(self.content_path, sub_dir)
            if not osp.isdir(abs_sub_dir):
                continue
            catalog_page_list[sub_dir] = []
            for f in os.listdir(abs_sub_dir):
                if not utils.check_extension(f):
                    continue
                fn = osp.join(abs_sub_dir, f)
                meta_yaml, contents = self.get_meta_and_content(fn)
                meta_datas = self.get_meta_datas(meta_yaml)
                r, e = osp.splitext(f)
                catalog_page_list[sub_dir].append({
                    "name" : r,
                    "title" : meta_datas["title"],
                    "date" : meta_datas["date"]
                })
            catalog_page_list[sub_dir].sort(
                key=lambda d: datetime.datetime.strptime(
                    d["date"], "%Y-%m-%d %H:%M"
                ),
                reverse=True,
            )

        tpl_vars = {
            "site" : self.site_settings,
            "catalog" : catalog_page_list,
        }

        return tpl_vars

    def generate_catalog_html(self):
        env = Environment(loader = FileSystemLoader(configs.TPL_PATH))
        tpl_vars = self.get_tpl_vars()
        html = env.get_template("index.html").render(tpl_vars)
        return html

    def update_catalog_page(self):
        catalog_html = self.generate_catalog_html()
        catalog_file = osp.join(self.output_path, "index.html")
        with codecs.open(catalog_file, "wb", "utf-8") as fd:
            fd.write(catalog_html)