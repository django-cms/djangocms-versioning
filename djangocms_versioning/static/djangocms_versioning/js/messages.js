// Hide all messages after timeout to prevent overlap of breadcrumbs
var djangoMessages = document.getElementsByClassName("messagelist");
setTimeout(function(){
    for (var i = 0; i < djangoMessages.length; i ++) {
        djangoMessages[i].setAttribute('style', 'display:none !important');
    }
}, 3000);
