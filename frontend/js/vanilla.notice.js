/**
*   This is a rewrite of Tim Benniks exellent jquery plugin in vanilla js using
*   modern browser features. Because it's 2023! :) 
* 
*   Released under the MIT license.
*   
*   Original copyright notice and license:
* 
*   jQuery.noticeAdd() and jQuery.noticeRemove()
*   These functions create and remove growl-like notices
*
*   Copyright (c) 2009 Tim Benniks
*
*   Permission is hereby granted, free of charge, to any person obtaining a copy
*   of this software and associated documentation files (the "Software"), to deal
*   in the Software without restriction, including without limitation the rights
*   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
*   copies of the Software, and to permit persons to whom the Software is
*   furnished to do so, subject to the following conditions:
*
*   The above copyright notice and this permission notice shall be included in
*   all copies or substantial portions of the Software.
*
*   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
*   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
*   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
*   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
*   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
*   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
*   THE SOFTWARE.
*/

function noticeAdd(options) {
  const defaults = {
    inEffect: { opacity: 'show' },
    inEffectDuration: 600,
    stayTime: 3000,
    text: '',
    stay: false,
    type: 'notice'
  };

  options = { ...defaults, ...options };
  const noticeWrapAll = document.querySelector('.notice-wrap') || document.createElement('div');
  noticeWrapAll.classList.add('notice-wrap');
  document.body.appendChild(noticeWrapAll);

  const noticeItemOuter = document.createElement('div');
  noticeItemOuter.classList.add('notice-item-wrapper');

  const noticeItemInner = document.createElement('div');
  noticeItemInner.classList.add('notice-item', options.type);
  noticeItemInner.innerHTML = `<p>${options.text}</p>`;
  noticeItemInner.style.display = 'none';
  noticeItemOuter.appendChild(noticeItemInner);
  noticeWrapAll.appendChild(noticeItemOuter);

  const noticeItemClose = document.createElement('div');
  noticeItemClose.classList.add('notice-item-close');
  noticeItemClose.innerHTML = 'x';
  noticeItemClose.addEventListener('click', function() {
    noticeItemInner.classList.remove('hasMouse');
    noticeRemove(noticeItemInner);
  });
  noticeItemInner.insertBefore(noticeItemClose, noticeItemInner.firstChild);

  if (navigator.userAgent.match(/MSIE 6/i)) {
    noticeWrapAll.style.top = document.documentElement.scrollTop + 'px';
  }

  if (!options.stay) {
    setTimeout(() => noticeRemove(noticeItemInner), options.stayTime);
  }

  noticeItemInner.addEventListener('mouseover', function() {
    noticeItemInner.classList.add('hasMouse');
  });

  noticeItemInner.addEventListener('mouseout', function() {
    noticeItemInner.classList.remove('hasMouse');
  });

  noticeItemInner.style.display = 'block';
  setTimeout(() => {
    noticeItemInner.animate(options.inEffect, options.inEffectDuration);
  }, 50);
}

function noticeRemove(obj) {
  if (obj.classList.contains('hasMouse')) {
    setTimeout(() => noticeRemove(obj), 1000);
    return;
  }

  obj.animate(
    { opacity: '0' },
    {
      duration: 600
    }
  ).addEventListener('finish', () => {
      obj.parentElement.remove();
  });
}