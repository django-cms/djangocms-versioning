(function($) {
    if (!$) {
        return;
    }

    // Hide django messages after timeout occurs to prevent content overlap
    $('document').ready(function(){
        // Targeting first item returned (there's only ever one messagelist per template):
        let messageList = document.getElementsByClassName("messagelist")[0];
        if(messageList != undefined){
          for(let item of messageList.children){
            item.style.opacity = 1;
            setTimeout(() => {
              let fader = setInterval(() => {
                item.style.opacity -= 0.05;
                  if(item.style.opacity < 0) {
                    item.style.display = "none";
                    clearInterval(fader);
                  }
              }, 20);
            }, 5000);
          }
        }
    });
 })((typeof django !== 'undefined' && django.jQuery) || (typeof CMS !== 'undefined' && CMS.$) || false);
