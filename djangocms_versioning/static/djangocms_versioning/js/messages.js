var djangoMessages = document.getElementsByClassName("messagelist");
setTimeout(function(){
    for (var i = 0; i < djangoMessages.length; i ++) {
        djangoMessages[i].setAttribute('style', 'visibility: hidden; opacity: 0; ' +
            'transition: visibility 0s linear 300ms, opacity 300ms; !important');
    }
}, 3000);
