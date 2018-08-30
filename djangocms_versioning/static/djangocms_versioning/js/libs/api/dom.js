(function dom__init() {
    'use strict';

    var MIN_ROWS_TO_HIDE = 5;
    var NUMBER_OF_CONTEXT_ROWS = 5;
    var nextUntil = function nextUntil(element, predicate) {
        var next = [];
        var el = element;

        while (el.nextSibling && !predicate(el.nextSibling)) {
            el = el.nextSibling;
            next.push(el);
        }

        return next;
    };

    /**
     * dropRight
     *
     * @public
     * @param {Array} array
     * @param {Number} n
     * @returns {Array}
     */
    function dropRight(array, n) {
        return array.length ? array.slice(0, n < 0 ? 0 : -n) : [];
    }

    /**
     * drop
     *
     * @public
     * @param {Array} array
     * @param {Number} n
     * @returns {Array}
     */
    function drop(array, n) {
        return array.length ? array.slice(n < 0 ? 0 : n, array.length) : [];
    }

    // namespace to test for web browser features for progressive enhancement
    // namespace for event handlers
    var event = {
        // allows visual folding of consecutive equal lines in a diff report
        difffold: function dom__event_difffold() {
            var row = this.parentNode;
            var rows;

            if (row.classList.contains('folded')) {
                row.classList.remove('folded');
                this.textContent = this.textContent.replace('+', '-');

                rows = nextUntil(row, function(r) {
                    if (r.classList.contains('foldable')) {
                        return false;
                    }
                    return true;
                });

                rows.forEach(function(r) {
                    r.style.display = 'table-row';
                });
            } else {
                row.classList.add('folded');
                this.textContent = this.textContent.replace('-', '+');

                rows = nextUntil(row, function(r) {
                    if (r.classList.contains('foldable')) {
                        return false;
                    }
                    return true;
                });

                rows.forEach(function(r) {
                    r.style.display = 'none';
                });
            }
        },
    };

    // alter tool on page load in reflection to saved state
    var load = function() {
        var difflist = document.getElementsByTagName('table');

        if (!difflist.length) {
            return;
        }
        var cells = difflist[0].getElementsByTagName('th');

        var foldableCells = Array.prototype.slice.call(cells).filter(function(cell) {
            return cell.classList.contains('fold');
        });

        foldableCells.forEach(function(cell, i) {
            if (cell.classList.contains('equal')) {
                var currentRow = cell.parentNode;
                var rows = nextUntil(cell.parentNode, function(r) {
                    var ths = r.getElementsByTagName('th');

                    if (ths && ths.length) {
                        var cls = ths[0].className;

                        if (cls && !cls.match('equal')) {
                            return true;
                        }
                    }

                    return false;
                });

                if (i === 0) {
                    rows = dropRight(rows, NUMBER_OF_CONTEXT_ROWS);
                } else if (i === foldableCells.length - 1) {
                    rows = drop(rows, NUMBER_OF_CONTEXT_ROWS - 1);
                } else {
                    rows = drop(dropRight(rows, NUMBER_OF_CONTEXT_ROWS), NUMBER_OF_CONTEXT_ROWS - 1);
                }

                if (currentRow.nextSibling === rows[0]) {
                    currentRow.classList.add('foldable');
                } else if (rows.length) {
                    cell.classList.remove('fold');
                    cell.textContent = cell.textContent.replace('- ', '');
                    cell = rows[0].children[0]; // eslint-disable-line no-param-reassign
                    cell.classList.add('fold');
                    cell.textContent = '- ' + cell.textContent;
                }

                cell.onclick = event.difffold;

                rows.forEach(function(row) {
                    row.classList.add('foldable');
                });

                if (rows.length > MIN_ROWS_TO_HIDE) {
                    cell.onclick();
                } else {
                    cell.classList.remove('fold');
                    currentRow.classList.remove('foldable');
                    cell.textContent = cell.textContent.replace('- ', '');
                }
            }
        });
    };

    window.onload = load;
})();
