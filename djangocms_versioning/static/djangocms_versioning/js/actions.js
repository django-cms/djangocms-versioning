(function($) {
    if (!$) {
        return;
    }

    $(function() {
        // INFO: it is not possible to put a form inside a form, so
        // the versioning actions have to create their own form on click.
        // Note for any apps inheriting the burger menu, this will also capture those events. 
        $(` .js-versioning-action,
            .cms-versioning-js-publish-btn, 
            .cms-versioning-js-edit-btn, 
            .cms-page-admin-action-burger-options-anchor`)
            .on('click', function(e) {
                e.preventDefault();

                var action = $(e.currentTarget);
                var formMethod = action.attr('class').indexOf('cms-form-get-method') !== -1 ? 'GET': 'POST';
                var csrfToken = formMethod == 'GET' ? '' : '<input type="hidden" name="csrfmiddlewaretoken" value="' +
                            document.cookie.match(/csrftoken=([^;]*);?/)[1] + '">';
                var fakeForm = $(
                    '<form style="display: none" action="' + action.attr('href') + '" method="' +
                           formMethod + '">' + csrfToken +
                    '</form>'
                );
                var keepSideFrame = action.attr('class').indexOf('js-versioning-keep-sideframe') !== -1;
                // always break out of the sideframe, cause it was never meant to open cms views inside it
                try {
                    if (!keepSideFrame)
                    {
                        window.top.CMS.API.Sideframe.close();
                    }
                } catch (err) {}
                if (keepSideFrame) {
                    var body = window.document.body;
                } else {
                    var body = window.top.document.body;
                }
                fakeForm.appendTo(body).submit();
            });

        $('.js-versioning-close-sideframe').on('click', function () {
            try {
                window.top.CMS.API.Sideframe.close();
            } catch (e) {}
        });
    });

    // Hide django messages after timeout occurs to prevent content overlap
    $('document').ready(function(){
        let djangoMessages = document.getElementsByClassName("messagelist");
        setTimeout(function(){
            for (var i = 0; i < djangoMessages.length; i ++) {
                djangoMessages[i].setAttribute('style', 'visibility: hidden; opacity: 0; ' +
                    'transition: visibility 0s linear 300ms, opacity 300ms; !important');
            }
        }, 3000);
    });

    // Create burger menu:
    $(function() {
        var createBurgerMenu = function createBurgerMenu(row) {
            var li;
            var text;
            var actions = $(row).children('.field-list_actions');
      
            if (!actions.length) {
              /* skip any rows without actions to avoid errors */
              return;
            }
            
            /* create burger menu anchor icon */
            var anchor = document.createElement('A');
            var cssclass = document.createAttribute('class');
            cssclass.value = 'btn cms-versioning-action-btn closed';
            anchor.setAttributeNode(cssclass);
            var title = document.createAttribute('title');
            title.value = 'Actions';
            anchor.setAttributeNode(title);
            var icon = document.createElement('IMG');
            var src = document.createAttribute('src');
            src.value = versioning_static_url_prefix + 'svg/menu.svg';
            icon.setAttributeNode(src);
            anchor.appendChild(icon);
            /* create options container */
      
            var optionsContainer = document.createElement('DIV');
            cssclass = document.createAttribute('class');
            cssclass.value = 'cms-pagetree-dropdown-menu ' + // main selector for the menu
            'cms-pagetree-dropdown-menu-arrow-right-top'; // keeps the menu arrow in position
      
            optionsContainer.setAttributeNode(cssclass);
            var ul = document.createElement('UL');
            cssclass = document.createAttribute('class');
            cssclass.value = 'cms-pagetree-dropdown-menu-inner';
            ul.setAttributeNode(cssclass);
            /* get the existing actions and move them into the options container */
      
      
            $(actions[0]).children('.cms-versioning-action-btn').each(function (index, item) {

              /* exclude some buttons */
              if (item.title == "Preview" || item.title == "Edit") {
                return;
              }
      
              li = document.createElement('LI');
              /* create an anchor from the item */
      
              var li_anchor = document.createElement('A');
              cssclass = document.createAttribute('class');
              cssclass.value = 'cms-page-admin-action-burger-options-anchor';
      
              if ($(item).hasClass('cms-form-get-method')) {
                /* ensure the fake-form selector is propagated to the new anchor */
                cssclass.value += ' cms-form-get-method';
              }
      
              li_anchor.setAttributeNode(cssclass);
              var href = document.createAttribute('href');
              href.value = $(item).attr('href');
              li_anchor.setAttributeNode(href);
              /* move the an image element */
      
              var existing_img = $(item).children('img');
              li_anchor.appendChild(existing_img[0]);
              /* create the button text */
      
              text = document.createTextNode(item.title);
              var span = document.createElement('SPAN');
              span.appendChild(text); // construct the button
      
              li.appendChild(li_anchor);
              li_anchor.appendChild(span);
              ul.appendChild(li);
              /* destroy original replaced buttons */
      
              actions[0].removeChild(item);
            });
            /* add the options to the drop-down */
      
            optionsContainer.appendChild(ul);
            actions[0].appendChild(anchor);
            document.body.appendChild(optionsContainer);
            /* listen for burger menu clicks */
      
            anchor.addEventListener('click', function (ev) {
              ev.stopPropagation();
              toggleBurgerMenu(anchor, optionsContainer);
            });
            /* close burger menu if clicking outside */
      
            $(window).click(function () {
              closeBurgerMenu();
            });
          };
      
          var toggleBurgerMenu = function toggleBurgerMenu(burgerMenuAnchor, optionsContainer) {
            var bm = $(burgerMenuAnchor);
            var op = $(optionsContainer);
            var closed = bm.hasClass('closed');
            closeBurgerMenu();
      
            if (closed) {
              bm.removeClass('closed');
              bm.addClass('open');
              op.removeClass('closed');
              op.addClass('open');
            } else {
              bm.addClass('closed');
              bm.removeClass('open');
              op.addClass('closed');
              op.removeClass('open');
            }
      
            var pos = bm.offset();
            op.css('left', pos.left - 200);
            op.css('top', pos.top);
          };
      
          var closeBurgerMenu = function closeBurgerMenu() {
            $('.cms-pagetree-dropdown-menu').removeClass('open');
            $('.cms-pagetree-dropdown-menu').addClass('closed');
            $('.cms-versioning-action-btn').removeClass('open');
            $('.cms-versioning-action-btn').addClass('closed');
          };
      
          $('#result_list').find('tr').each(function (index, item) {
            createBurgerMenu(item);
          });

    });

})((typeof django !== 'undefined' && django.jQuery) || (typeof CMS !== 'undefined' && CMS.$) || false);
