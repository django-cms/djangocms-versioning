import diff from 'htmldiff';
import srcDoc from 'srcdoc-polyfill';
import memoize from 'lodash.memoize';
import { showLoader, hideLoader } from './loader';
import { getData } from './utils';
import getDistPath from './get-dist-path';
import versioningCSS from '../css/versioning.css';

const memoizedDiff = memoize(diff);


__webpack_public_path__ = getDistPath('bundle.versioning');

const getCurrentMarkup = () => {
    return fetch(getData('v2_url'))
        .then(response => response.text());
};

const getPublishedMarkup = () => {
    return fetch(getData('v1_url'))
        .then(response => response.text());
};

const getOrAddFrame = () => {
    let frame = document.querySelector('.js-cms-versioning-diff-frame');

    if (frame) {
        return frame;
    }

    frame = document.createElement('iframe');
    frame.className = 'js-cms-versioning-diff-frame cms-versioning-diff-frame';

    document.getElementById('cms-top').appendChild(frame);

    return frame;
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

        const styleElement = document.createElement('style');

        styleElement.textContent = versioningCSS;
        newDoc.body.appendChild(styleElement);

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

        const scriptElement = document.createElement('script');

        scriptElement.textContent = prettydiff.default.js;
        newDoc.head.appendChild(scriptElement);

        const styleElement = document.createElement('style');

        styleElement.textContent = prettydiff.default.styles;
        newDoc.head.appendChild(styleElement);

        srcDoc.set(frame, newDoc.documentElement.outerHTML);
    });
};

const initControls = () => {
    document.querySelectorAll('.js-cms-versioning-control-visual').forEach(button => {
        button.addEventListener('click', e => {
            e.preventDefault();

            if (button.classList.contains('cms-btn-active')) {
                return;
            }

            document.querySelectorAll('.js-cms-versioning-control').forEach(el => {
                el.classList.remove('cms-btn-active');
            });
            button.classList.add('cms-btn-active');

            showVisual();
        });
    });

    document.querySelectorAll('.js-cms-versioning-control-source').forEach(button => {
        button.addEventListener('click', e => {
            e.preventDefault();

            if (button.classList.contains('cms-btn-active')) {
                return;
            }

            document.querySelectorAll('.js-cms-versioning-control').forEach(el => {
                el.classList.remove('cms-btn-active');
            });
            button.classList.add('cms-btn-active');

            showSource();
        });
    });

    document.querySelectorAll('.js-cms-versioning-version').forEach(select => {
        select.addEventListener('change', e => {
            switchVersion(e.target.value);
        });
    });
};

// in case the view is loaded inside the cms sideframe,
// or any link on the page that is being diffed is clicked and this bundle loads there
const breakOutOfAnIframe = () => {
    try {
        window.top.CMS.API.Sideframe.close();
    } catch {}
    setTimeout(function () {
        if (window.parent && window.parent !== window) {
            window.top.location.href = window.location.href;
        }
    }, 0);
};

const showControls = () => {
    const controlsElement = document.querySelector('.cms-versioning-controls .cms-toolbar-item-buttons .cms-btn-group');

    if (controlsElement) {
        controlsElement.style.display = 'block';
    }
};

document.addEventListener('DOMContentLoaded', function() {
    breakOutOfAnIframe();
    initControls();

    if (getData('v2_url')) {
        showControls();
        showVisual();
    }
});
