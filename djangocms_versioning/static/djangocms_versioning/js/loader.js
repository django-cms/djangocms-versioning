import Nprogress from 'nprogress';
import debounce from 'lodash.debounce';

Nprogress.configure({
    showSpinner: false,
    parent: '#cms-top',
    trickleSpeed: 200,
    minimum: 0.3,
    template: `
        <div class="cms-loading-bar" role="bar">
            <div class="cms-loading-peg"></div>
        </div>
    `
});

export const showLoader = debounce(() => {
    Nprogress.start();
}, 0);

export const hideLoader = () => {
    showLoader.cancel();
    Nprogress.done();
};
