import $ from 'jquery';

let data;

$(function () {
    data = $('#cms-top').data('compare');
});

export const getData = prop => data && data[prop];
