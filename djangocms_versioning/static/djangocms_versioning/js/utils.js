let data;

document.addEventListener('DOMContentLoaded', function() {
    data = JSON.parse(document.getElementById('cms-top').dataset.compare);
});

export const getData = prop => data && data[prop];
