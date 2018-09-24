import diff from 'htmldiff';
import $ from 'jquery';
import srcDoc from 'srcdoc-polyfill';
import memoize from 'lodash.memoize';
import { showLoader, hideLoader } from './loader';
import { getData } from './utils';

const memoizedDiff = memoize(diff);

// eslint-disable-next-line
__webpack_public_path__ = require('./get-dist-path')('bundle.versioning');

const getCurrentMarkup = () => {
    return $.ajax({
        url: getData('v2_url')
    }).then(markup => markup);
};

const getPublishedMarkup = () => {
    return $.ajax({
        url: getData('v1_url')
    }).then(markup => markup);
};

const getOrAddFrame = () => {
    let frame = $('.js-cms-versioning-diff-frame');

    if (frame.length) {
        return frame[0];
    }

    frame = $('<iframe class="js-cms-versioning-diff-frame cms-versioning-diff-frame"></iframe>');

    $('#cms-top').append(frame);

    return frame[0];
};

const switchVersion = version => {
    const url = window.location.href;

    if (url.match(/compare_to=\d+/)) {
        window.location.href = window.location.href.replace(/compare_to=\d+/, `compare_to=${version}`);
    } else if (url.match(/\?/)) {
        window.location.href += `&compare_to=${version}`;
    } else {
        window.location.href += `?compare_to=${version}`;
    }
};

let p;

const loadMarkup = () => {
    if (!p) {
        showLoader();
        p = Promise.all([
            getCurrentMarkup(),
            getPublishedMarkup(),
        ]).then(r => {
            hideLoader();
            return r;
        });
    }
    return p;
};

const showVisual = () => {
    loadMarkup().then(([current, published]) => {
        const result = memoizedDiff(published, current, 'cms-diff');
        const frame = getOrAddFrame();

        var newDoc = new DOMParser().parseFromString(result, 'text/html');

        $(newDoc).find('body').append(`<style>${require('../css/versioning.css')}</style>`);

        srcDoc.set(frame, newDoc.documentElement.outerHTML);
    });
};

const showSource = () => {
    showLoader();
    Promise.all([
        import(
            /* webpackChunkName: "prettydiff" */
            'prettydiff'
        ),
        loadMarkup(),
    ]).then(([prettydiff, [current, published]]) => {
        hideLoader();
        const frame = getOrAddFrame();
        const markup = prettydiff.default.diff(
            published,
            current
        );

        var newDoc = new DOMParser().parseFromString(markup, 'text/html');

        $(newDoc).find('head').append(`
            <script>
                ${prettydiff.default.js}
            </script>
            <style>
                ${prettydiff.default.styles}
            </style>
        `);

        srcDoc.set(frame, newDoc.documentElement.outerHTML);
    });
};

const initControls = () => {
    $('.js-cms-versioning-control-visual').on('click', e => {
        e.preventDefault();
        const button = $(e.currentTarget);

        if (button.is('.cms-btn-active')) {
            return;
        }

        $('.js-cms-versioning-control').removeClass('cms-btn-active');
        button.addClass('cms-btn-active');

        showVisual();
    });

    $('.js-cms-versioning-control-source').on('click', e => {
        e.preventDefault();
        const button = $(e.currentTarget);

        if (button.is('.cms-btn-active')) {
            return;
        }

        $('.js-cms-versioning-control').removeClass('cms-btn-active');
        button.addClass('cms-btn-active');

        showSource();
    });

    $('.js-cms-versioning-version').on('change', e => {
        switchVersion(e.target.value);
    });
};

// in case the view is loaded inside the cms sideframe,
// or any link on the page that is being diffed is clicked and this bundle loads there
const breakOutOfAnIframe = () => {
    try {
        window.top.CMS.API.Sideframe.close();
    } catch (e) {}
    setTimeout(function () {
        if (window.parent && window.parent !== window) {
            window.top.location.href = window.location.href;
        }
    }, 0);
};

const showControls = () => $('.cms-versioning-controls .cms-toolbar-item-buttons .cms-btn-group').show();

$(function() {
    breakOutOfAnIframe();
    initControls();

    if (getData('v2_url')) {
        showControls();
        showVisual();
    }
});
