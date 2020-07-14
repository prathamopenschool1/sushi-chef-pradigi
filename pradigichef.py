#!/usr/bin/env python3


from cachecontrol.heuristics import OneDayCache
import copy
import json
import logging
import os
import requests
import shutil
import time
from pprint import pprint
from le_utils.constants import content_kinds, file_types, licenses
from le_utils.constants.languages import getlang
from ricecooker.chefs import JsonTreeChef
from ricecooker.classes.licenses import get_license
from ricecooker.config import LOGGER
from ricecooker.utils.caching import FileCache, CacheControlAdapter
from ricecooker.utils.jsontrees import write_tree_to_json_tree
from ricecooker.classes.files import Image

from transform import HTML5APP_ZIPS_LOCAL_DIR
from transform import get_zip_file
from transform import get_phet_zip_file
from corrections import should_skip_file

PRADIGI_DOMAIN = 'prathamopenschool.org'
PRADIGI_SOURCE_ID__VARIANT_PRATHAM = 'pradigi-videos-and-games'  # Pratham internal
PRADIGI_SOURCE_ID__VARIANT_LE = 'pradigi-channel'  # Studio PUBLIC channel
FULL_DOMAIN_URL = 'https://www.' + PRADIGI_DOMAIN
PRADIGI_LICENSE = get_license(licenses.CC_BY_NC_SA, copyright_holder='PraDigi').as_dict()
PRADIGI_WEBSITE_LANGUAGES = ['Hindi']
PRADIGI_DESCRIPTION = 'Developed by Pratham, these educational games, videos, ' \
                      'and ebooks are designed to teach language learning, math, science, English, ' \
                      'health, and vocational training in Hindi, Marathi, Odia, Bengali, Urdu, ' \
                      'Punjabi, Kannada, Tamil, Telugu, Gujarati and Assamese. Materials are ' \
                      'designed for learners of all ages, including those outside the formal classroom setting.'

# In debug mode, only one topic is downloaded.
LOGGER.setLevel(logging.DEBUG)
DEBUG_MODE = True  # source_urls in content desriptions

# WebCache logic (downloaded web resources cached for one day -- good for dev)
cache = FileCache('.webcache')
basic_adapter = CacheControlAdapter(cache=cache)
develop_adapter = CacheControlAdapter(heuristic=OneDayCache(), cache=cache)
session = requests.Session()
session.mount('http://www.' + PRADIGI_DOMAIN, develop_adapter)
session.mount('https://www.' + PRADIGI_DOMAIN, develop_adapter)

CHEF_DIR = os.path.dirname(os.path.realpath(__file__))
print(CHEF_DIR)

# LOCALIZATION AND TRANSLATION STRINGS
################################################################################
PRADIGI_STRINGS = {
    'hi': {
        'language_en': 'Hindi',
        'website_lang': 'hn',
        'gamesrepo_suffixes': ['_KKS', '_HI', '_Hi'],
    },
    "mr": {
        "language_en": "Marathi",
        'website_lang': 'mr',
        "gamesrepo_suffixes": ['_KKS', '_MR', '_M'],
    },
    'en': {
        'language_en': 'English',
        'gamesrepo_suffixes': [],
    },
    "or": {
        "language_en": "Odia",  # also appears as Odia in CntResource.lang_name
        'website_lang': 'Od',
        "gamesrepo_suffixes": ['_OD'],
    },
    "bn": {
        "language_en": "Bengali",  # Bengali in CntResource.lang_name
        "gamesrepo_suffixes": ['_BN'],
    },
    "ur": {
        "language_en": "Urdu",
        "gamesrepo_suffixes": ['_UD'],
    },
    "pnb": {
        "language_en": "Punjabi",
        'website_lang': 'Pn',
        "gamesrepo_suffixes": ['_PN'],
    },
    "kn": {
        "language_en": "Kannada",
        "gamesrepo_suffixes": ['_KN'],
    },
    "ta": {
        "language_en": "Tamil",
        'website_lang': 'Tm',
        "gamesrepo_suffixes": ['_TM'],
    },
    "te": {
        "language_en": "Telugu",
        'website_lang': 'Tl',
        "gamesrepo_suffixes": ['_TL'],
    },
    "gu": {
        'website_lang': 'Gj',
        "language_en": "Gujarati",
        "gamesrepo_suffixes": ['_KKS', '_GJ', '_Gj'],
    },
    "as": {
        "language_en": "Assamese",
        "gamesrepo_suffixes": ['_AS'],
    },
}

# RICECOOKER JSON TRANSFORMATIONS
################################################################################


# with open("chefdata/trees/pradigi_hindi_web_resource_tree.json", 'r', encoding='utf-8') as jtree:
#     web_resource_tree = json.load(jtree)
# web_resource_tree_children = web_resource_tree['children']

LANGUAGE_CODE_LOOKUP = {}
for lang_code, lang_info in PRADIGI_STRINGS.items():
    LANGUAGE_CODE_LOOKUP[lang_info["language_en"]] = lang_code

print("LANGUAGE_CODE_LOOKUP=", LANGUAGE_CODE_LOOKUP)
print('LANGUAGE_CODE_LOOKUP["Hindi"]=', LANGUAGE_CODE_LOOKUP["Hindi"])
# time.sleep(1)

import subprocess
from ricecooker.utils.html import download_file

# Wav files download
DOWNLOADED_WAV_FILES_DIR = os.path.join("chefdata", "downloadedwavs")
print(DOWNLOADED_WAV_FILES_DIR, 'DOWNLOADED_WAV_FILES_DIR')
if not os.path.exists(DOWNLOADED_WAV_FILES_DIR):
    os.makedirs(DOWNLOADED_WAV_FILES_DIR, exist_ok=True)
    print("done")
CONVERTED_MP3_FILES_DIR = os.path.join("chefdata", "convertedmp3s")
print(CONVERTED_MP3_FILES_DIR, 'CONVERTED_MP3_FILES_DIR')
if not os.path.exists(CONVERTED_MP3_FILES_DIR):
    os.makedirs(CONVERTED_MP3_FILES_DIR, exist_ok=True)
    print("done1")


# / @DJ: move lines  /\   /\   /\   to top of file

def download_and_convert_wav_file(wav_url):
    """
    Kolibri AudioNode only support .mp3 files and not .wav, so we must convert.
    """
    wav_filename = wav_url.split('/')[-1]  # e.g. something.wav
    wav_path = os.path.join(DOWNLOADED_WAV_FILES_DIR, wav_filename)
    print("done3")

    # 1. DOWNLOAD
    download_file(wav_url, DOWNLOADED_WAV_FILES_DIR)
    print("don4")

    # 2. CONVERT
    mp3_filename = wav_filename.replace('.wav', '.mp3')
    mp3_path = os.path.join(CONVERTED_MP3_FILES_DIR, mp3_filename)
    print(mp3_filename, mp3_path)
    if not os.path.exists(mp3_path):
        try:
            command = ["ffmpeg", "-i", wav_path, "-acodec", "mp3", "-ac", "2",
                       "-ab", "64k", "-y", "-hide_banner", "-loglevel", "warning", mp3_path]
            subprocess.check_call(command)
            print("Successfully converted wav file to mp3")
        except subprocess.CalledProcessError:
            print("Problem converting " + wav_url)
            return None

    # Return path of converted mp3 file
    return mp3_path


def wrt_to_ricecooker_tree(tree, filter_fn=lambda node: True):
    """
    Transforms web resource subtree `tree` into a ricecooker tree of topics nodes,
    and content nodes, using `filter_fn` to determine if each node should be included or not.
    """
    global topic_node
    kind = tree['kind']
    print(kind, 'kind')
    if kind == 'Topic':
        thumbnail = tree['cont_thumburl'] if 'cont_thumburl' in tree else None
        topic_node = dict(
            kind=content_kinds.TOPIC,
            source_id=tree['content_id'],
            language=LANGUAGE_CODE_LOOKUP[tree['cont_lang']],
            title=tree['cont_title'],  # or could get from Strings based on subject_en...
            description='source_id=' + tree['content_id'] if DEBUG_MODE else '',
            thumbnail=thumbnail,
            license=PRADIGI_LICENSE,
            children=[],
        )
        source_ids_seen_so_far = []
        for child in tree['children']:
            # print(child, 'childdd..')
            if filter_fn(child):
                try:
                    ricecooker_node = wrt_to_ricecooker_tree(child, filter_fn=filter_fn)
                    # print(ricecooker_node['source_id'], 'ricecooker_node')
                    if ricecooker_node:
                        new_source_id = ricecooker_node['source_id']
                        # print(new_source_id, 'new_source_id')
                        if new_source_id not in source_ids_seen_so_far:
                            topic_node['children'].append(ricecooker_node)
                            source_ids_seen_so_far.append(new_source_id)
                            # print(source_ids_seen_so_far, 'source_ids_seen_so_far')
                        else:
                            print('Skipping node with duplicate source_id', ricecooker_node)
                except Exception as e:
                    LOGGER.error("Failed to generate node for %s in %s in %s " %
                                 (child['cont_title'], child['age_group'], e))
                    print(e)
                    pass
        # print(topic_node, 'topic')
        return topic_node
    elif kind == 'PrathamVideoResource':
        thumbnail = tree['cont_thumburl'] if 'cont_thumburl' in tree else None
        video_node = dict(
            kind=content_kinds.VIDEO,
            source_id=tree['content_id'],
            language=LANGUAGE_CODE_LOOKUP[tree['cont_lang']],
            title=tree['cont_title'],
            description=tree.get('resource_desc', ''),
            thumbnail=thumbnail,
            license=PRADIGI_LICENSE,
            files=[],
        )
        video_url = tree['cont_dwurl']
        if video_url.endswith('.MP4'):
            video_url = video_url.replace('.MP4', '.mp4')
        elif video_url.endswith('.m4v'):
            video_url = video_url.replace('.m4v', '.mp4')
        video_file = dict(
            file_type=file_types.VIDEO,
            path=video_url,
            language=LANGUAGE_CODE_LOOKUP[tree['cont_lang']],
        )
        if should_compress_video(tree):
            video_file['ffmpeg_settings'] = {"crf": 28}  # average quality
        video_node['files'].append(video_file)
        # print(video_node, 'video_node')
        return video_node

    elif kind == 'PrathamAudioResource':
        thumbnail = tree['cont_thumburl'] if 'cont_thumburl' in tree else None
        audio_node = dict(
            kind=content_kinds.AUDIO,
            source_id=tree['content_id'],
            language=LANGUAGE_CODE_LOOKUP[tree['cont_lang']],
            title=tree['cont_title'],
            description=tree.get('resource_desc', ''),
            thumbnail=thumbnail,
            license=PRADIGI_LICENSE,
            files=[],
        )
        audio_url = tree['cont_dwurl']
        print(audio_url, 'audiourl')
        if audio_url.endswith('.wav'):
            audio_url = download_and_convert_wav_file(audio_url)
        elif audio_url.endswith('.MP3'):
            audio_url = audio_url.replace('.MP3', '.mp3')
        audio_file = dict(
            file_type=file_types.AUDIO,
            path=audio_url,
            language=LANGUAGE_CODE_LOOKUP[tree['cont_lang']],
        )
        audio_node['files'].append(audio_file)
        return audio_node

    elif kind == 'PrathamZipResource':
        if should_skip_file(tree['cont_dwurl']):
            return None  # Skip games marked with the `SKIP GAME` correction actions
        thumbnail = tree['cont_thumburl'] if 'cont_thumburl' in tree else None
        html5_node = dict(
            kind=content_kinds.HTML5,
            source_id=tree['content_id'],
            language=LANGUAGE_CODE_LOOKUP[tree['cont_lang']],
            title=tree['cont_title'],
            description=tree.get('resource_desc', ''),
            thumbnail=thumbnail,
            license=PRADIGI_LICENSE,
            files=[],
        )
        if 'phet.zip' in tree['cont_dwurl']:
            zip_tmp_path = get_phet_zip_file(tree['cont_dwurl'], tree['cont_url'])
        else:
            zip_tmp_path = get_zip_file(tree['cont_dwurl'], tree['cont_url'])
        if zip_tmp_path is None:
            raise ValueError('Could not get zip file from %s' % tree['cont_url'])
        html5zip_file = dict(
            file_type=file_types.HTML5,
            path=zip_tmp_path,
            language=LANGUAGE_CODE_LOOKUP[tree['cont_lang']],
        )
        html5_node['files'].append(html5zip_file)
        # print(html5_node, 'zipnode')
        return html5_node

    elif kind == 'PrathamPdfResource' or kind == 'story_resource_page':
        thumbnail = tree['cont_thumburl'] if 'cont_thumburl' in tree else None
        pdf_node = dict(
            kind=content_kinds.DOCUMENT,
            source_id=tree['content_id'],
            language=LANGUAGE_CODE_LOOKUP[tree['cont_lang']],
            title=tree['cont_title'],
            description=tree.get('resource_desc', ''),
            thumbnail=thumbnail,
            license=PRADIGI_LICENSE,
            files=[],
        )
        pdf_file = dict(
            file_type=file_types.DOCUMENT,
            path=tree['cont_dwurl'],
            language=LANGUAGE_CODE_LOOKUP[tree['cont_lang']],
        )
        pdf_node['files'].append(pdf_file)
        # print(pdf_node, 'pdf')
        return pdf_node

    else:
        raise ValueError('Unknown web resource kind ' + kind + ' encountered.')


def should_compress_video(video_web_resource):
    """
    Make HEAD request to obtain the `content-length` of the `video_web_resource`.
    Web-optimized videos do not need to be re-encoded and compressed: it's better
    to upload to Studio the original files. We compress large vidoes (> 30MB) in
    order to limit storage and transfer needs.
    """
    video_url = video_web_resource['cont_dwurl']
    head_response = requests.head(video_url)
    if head_response:
        content_length = head_response.headers.get('content-length', None)
        if content_length:
            size_mb = int(content_length) / 1024 / 1024
            if size_mb > 30:
                return True
    return False


# Test the wrt_to_ricecooker_tree function on samples of each content kind
RESOURCE_SAMPLES = [
    'sample_PrathamVideoResource.json',
    'sample_PrathamZipResource.json',
    'sample_PrathamPdfResource.json',
    'sample_PrathamAudioResource.json',
    'sample_Topic.json',
]
#
# for resource_sample in RESOURCE_SAMPLES:
#     print('\n\nLoading sample from', resource_sample)
#     sample_path = os.path.join('chefdata', 'trees', resource_sample)
#     with open(sample_path, 'r', encoding='utf-8') as jtree:
#         web_resource_tree = json.load(jtree)
#         web_resource_tree_children = web_resource_tree['children']
#         tree_sample = web_resource_tree_children[0]  # a single node
#         ricecooker_subtree = wrt_to_ricecooker_tree(tree_sample)
#         pprint(ricecooker_subtree)
#         time.sleep(1)
        # return ricecooker_subtree

# import sys
#
# sys.exit(1)  # EXIT here; do not try to run chef

# CHEF
###############################################################################


class PraDigiChef(JsonTreeChef):
    """
    SushiChef script for importing and merging the content from these sources:
      - Video, PDFs, and interactive demos from http://www.prathamopenschool.org/
      - Games from http://www.prathamopenschool.org/
    """
    RICECOOKER_JSON_TREE = 'pradigi_ricecooker_json_tree.json'

    def pre_run(self, args, options):
        """
        Build the ricecooker json tree for the entire channel
        """
        LOGGER.info('in pre_run...')

        # Conditionally determine `source_id` depending on variant specified
        if 'variant' in options and options['variant'].upper() == 'LE':
            # Official PraDigi channel =
            channel_name = 'PraDigi'
            channel_source_id = PRADIGI_SOURCE_ID__VARIANT_LE
            DEBUG_MODE = False
        else:
            # Pratham ETL (used to import content from website into Pratham app)
            # channel_id = f9da12749d995fa197f8b4c0192e7b2c
            channel_name = 'Pratham PraDigi'
            # channel_source_id = PRADIGI_SOURCE_ID__VARIANT_PRATHAM
            channel_source_id = PRADIGI_SOURCE_ID__VARIANT_PRATHAM + '_testing'

        ricecooker_json_tree = dict(
            title=channel_name,
            source_domain=PRADIGI_DOMAIN,
            source_id=channel_source_id,
            description=PRADIGI_DESCRIPTION,
            thumbnail='chefdata/plogo.jpg',
            language='mul',
            children=[],
        )

        # for resource_sample in RESOURCE_SAMPLES:
        #     print('\n\nLoading sample from', resource_sample)
        #     sample_path = os.path.join('chefdata', 'trees', resource_sample)
        #     with open(sample_path, 'r', encoding='utf-8') as jtree:
        #         web_resource_tree = json.load(jtree)
        #         web_resource_tree_children = web_resource_tree['children']
        #         tree_sample = web_resource_tree_children[0]  # a single node
        #         ricecooker_subtree = wrt_to_ricecooker_tree(tree_sample)
        #         pprint(ricecooker_subtree)
        #         ricecooker_json_tree['children'].append(ricecooker_subtree)
        #         time.sleep(1)
        # once all the samples work you can try the full tree
        with open("chefdata/trees/pradigi_hindi_web_resource_tree.json", 'r', encoding='utf-8') as jtree:
            web_resource_tree = json.load(jtree)
            web_resource_tree_children = web_resource_tree['children']
            for lang_subtree in web_resource_tree_children:
                ricecooker_subtree = wrt_to_ricecooker_tree(lang_subtree)
                print(ricecooker_subtree, 'subtree0')
                ricecooker_json_tree['children'].append(ricecooker_subtree)
        print(ricecooker_json_tree, 'subtree1')
        json_tree_path = self.get_json_tree_path()
        write_tree_to_json_tree(json_tree_path, ricecooker_json_tree)

    def run(self, args, options):
        print('options=', options, flush=True)
        if 'crawlonly' in options:
            self.pre_run(args, options)
            print('Crawling done. Skipping rest of chef run since `crawlonly` is set.')
            return
        super(PraDigiChef, self).run(args, options)


# CLI
#############################################################################

if __name__ == '__main__':
    pradigi_chef = PraDigiChef()
    pradigi_chef.main()
