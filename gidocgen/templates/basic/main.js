// SPDX-FileCopyrightText: 2021 GNOME Foundation
// SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

// eslint-disable-next-line no-unused-vars
function hasClass(elem, className) {
    return elem && elem.classList && elem.classList.contains(className);
}

// eslint-disable-next-line no-unused-vars
function addClass(elem, className) {
    if (!elem || !elem.classList) {
        return;
    }
    elem.classList.add(className);
}

// eslint-disable-next-line no-unused-vars
function removeClass(elem, className) {
    if (!elem || !elem.classList) {
        return;
    }
    elem.classList.remove(className);
}

function insertAfter(newNode, referenceNode) {
    referenceNode.parentNode.insertBefore(newNode, referenceNode.nextSibling);
}

function onEach(arr, func, reversed) {
    if (arr && arr.length > 0 && func) {
        var length = arr.length;
        var i;
        if (reversed !== true) {
            for (i = 0; i < length; ++i) {
                if (func(arr[i]) === true) {
                    return true;
                }
            }
        } else {
            for (i = length - 1; i >= 0; --i) {
                if (func(arr[i]) === true) {
                    return true;
                }
            }
        }
    }
    return false;
}

function onEachLazy(lazyArray, func, reversed) {
    return onEach(
        Array.prototype.slice.call(lazyArray),
        func,
        reversed);
}

// eslint-disable-next-line no-unused-vars
function hasOwnProperty(obj, property) {
    return Object.prototype.hasOwnProperty.call(obj, property);
}

window.addEventListener("load", function() {
    "use strict;"

    var main = document.getElementById("main");
    var btnToTop = document.getElementById("btn-to-top");

    function labelForToggleButton(isCollapsed) {
        if (isCollapsed) {
            return "+";
        }
        return "\u2212";
    }

    function createToggle(isCollapsed) {
        var toggle = document.createElement("a");
        toggle.href = "javascript:void(0)";
        toggle.className = "collapse-toggle";
        toggle.innerHTML = "[<span class=\"inner\">"
                         + labelForToggleButton(isCollapsed)
                         + "</span>]";

        return toggle;
    }

    function toggleClicked() {
        if (hasClass(this, "collapsed")) {
            removeClass(this, "collapsed");
            this.innerHTML = "[<span class=\"inner\">"
                           + labelForToggleButton(false)
                           + "</span>]";
            onEachLazy(this.parentNode.getElementsByClassName("docblock"), function(e) {
                removeClass(e, "hidden");
            });
        } else {
            addClass(this, "collapsed");
            this.innerHTML = "[<span class=\"inner\">"
                           + labelForToggleButton(true)
                           + "</span>]";
            onEachLazy(this.parentNode.getElementsByClassName("docblock"), function(e) {
                addClass(e, "hidden");
            });
        }
    }

    onEachLazy(document.getElementsByClassName("toggle-wrapper"), function(e) {
        collapsedByDefault = hasClass(e, "default-hide");
        var toggle = createToggle(collapsedByDefault);
        toggle.onclick = toggleClicked;
        e.insertBefore(toggle, e.firstChild);
        if (collapsedByDefault) {
            addClass(toggle, "collapsed");
            onEachLazy(e.getElementsByClassName("docblock"), function(d) {
                addClass(d, "hidden");
            });
        }
    });

    function scrollBackTop(e) {
        e.preventDefault();
        window.scroll({
            top: 0,
            behavior: 'smooth',
        });
    }

    function toggleScrollButton() {
        if (window.scrollY < 400) {
            addClass(btnToTop, "hidden");
        } else {
            removeClass(btnToTop, "hidden");
        }
    }

    function resolveNamespaceLink(namespace) {
        try {
            let urlMap = new Map(baseURLs);
            if (urlMap.has(namespace)) {
                return urlMap.get(namespace);
            }
            return '';
        } catch (e) {
            return '';
        }
    }

    window.onscroll = toggleScrollButton;
    btnToTop.onclick = scrollBackTop;

    onEachLazy(document.getElementsByClassName("external"), function(e) {
        if (e.tagName == "A" && e.dataset.hasOwnProperty('namespace')) {
            var data_namespace = e.dataset.namespace
            var data_link = e.dataset.link
            var base_url = resolveNamespaceLink(data_namespace)
            if (base_url !== '') {
                e.href = base_url + data_link;
            } else {
                e.title = "No reference to the " + data_namespace + " namespace";
            }
        }
    });
}, false);
