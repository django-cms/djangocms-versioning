import styles from '../css/source.css';
import diffview from './libs/diffview';
import difflib from './libs/difflib';
import tidy from './libs/tidy';
import js from './libs/api/dom';
import memoize from 'lodash.memoize';
import { getData } from './utils';

const buildView = memoize(diffview.buildView);

/**
 * Returns markup of a diff view
 *
 * @public
 * @param {String} before
 * @param {String} after
 * @returns {String}
 */
function diff(before, after) {
    // http://api.html-tidy.org/tidy/quickref_5.6.0.html
    const tidyConfig = {
        indent: true,
        'indent-spaces': 4,
        wrap: 80,
        markup: true,
        'output-xml': false,
        'numeric-entities': true,
        'quote-marks': true,
        'quote-nbsp': false,
        'show-body-only': false,
        'quote-ampersand': false,
        'break-before-br': true,
        'uppercase-tags': false,
        'uppercase-attributes': false,
        'drop-font-tags': false,
        'tidy-mark': false,
        'drop-empty-elements': false,
        'drop-empty-paras': false,
        clean: false,
        'merge-divs': false,
        'merge-spans': false,
        'preserve-entities': true,
        // 'fix-style-tags': false,
        // 'escape-scripts': false,
        'fix-backslash': false,
        'fix-bad-comments': false,
        'fix-uri': false,
        // 'skip-nested': false,
        'join-styles': false,
        'merge-emphasis': false,
        'replace-color': false,
    };
    const beforeLines = difflib.stringAsLines(tidy(before, tidyConfig));
    const afterLines = difflib.stringAsLines(tidy(after, tidyConfig));
    const sm = new difflib.SequenceMatcher(beforeLines, afterLines);
    const opcodes = sm.get_opcodes();

    return buildView({
        baseTextLines: beforeLines,
        newTextLines: afterLines,
        opcodes: opcodes,
        baseTextName: getData('v1_description') || 'Published',
        newTextName: getData('v2_description') || 'Current',
        contextSize: null,
        viewType: 0,
    }).outerHTML;
}

export default {
    diff,
    styles,
    js,
};
