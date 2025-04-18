/** @odoo-module **/

/**
 * The jquery library extensions and fixes should be done here to avoid patching
 * in place.
 */

// jQuery selectors extensions
$.extend($.expr[':'], {
    containsLike: function (element, index, matches){
        return element.innerHTML.toUpperCase().indexOf(matches[3].toUpperCase()) >= 0;
    },
    containsTextLike: function (element, index, matches){
        return element.innerText.toUpperCase().indexOf(matches[3].toUpperCase()) >= 0;
    },
    containsExact: function (element, index, matches){
        return $.trim(element.innerHTML) === matches[3];
    },
    containsExactText: function (element, index, matches) {
        return element.innerText.trim() === matches[3].trim();
    },
    /**
     * Note all escaped characters need to be double escaped inside of the
     * expression, so "\(" needs to be "\\("
     */
    containsRegex: function (element, index, matches){
        var regreg =  /^\/((?:\\\/|[^\/])+)\/([mig]{0,3})$/,
        reg = regreg.exec(matches[3]);
        return reg ? new RegExp(reg[1], reg[2]).test($.trim(element.innerHTML)) : false;
    },
    propChecked: function (element, index, matches) {
        return $(element).prop("checked") === true;
    },
    propSelected: function (element, index, matches) {
        return $(element).prop("selected") === true;
    },
    propValue: function (element, index, matches) {
        return $(element).prop("value") === matches[3];
    },
    propValueContains: function (element, index, matches) {
        return $(element).prop("value") && $(element).prop("value").indexOf(matches[3]) !== -1;
    },
    hasData: function (element) {
        return !!_.toArray(element.dataset).length;
    },
    data: function (element, index, matches) {
        return $(element).data(matches[3]);
    },
    hasVisibility: function (element, index, matches) {
        var $element = $(element);
        if ($(element).css('visibility') === 'hidden') {
            return false;
        }
        var $parent = $element.parent();
        if (!$parent.length || $element.is('html')) {
            return true;
        }
        return $parent.is(':hasVisibility');
    },
    hasOpacity: function (element, index, matches) {
        var $element = $(element);
        if (parseFloat($(element).css('opacity')) <= 0.01) {
            return false;
        }
        var $parent = $element.parent();
        if (!$parent.length || $element.is('html')) {
            return true;
        }
        return $parent.is(':hasOpacity');
    },
});

// jQuery functions extensions
$.fn.extend({
    /**
     * Returns all the attributes of a DOM element (first one in the jQuery
     * set).
     *
     * @returns {Object} attribute name -> attribute value
     */
    getAttributes: function () {
        var o = {};
        if (this.length) {
            var attrs = this[0].attributes;
            for (var i = 0, l = attrs.length ; i < l ; i++) {
                var attr = attrs.item(i);
                o[attr.name] = attr.value;
            }
        }
        return o;
    },
    /**
     * Makes DOM elements bounce the way Odoo decided it.
     *
     * @param {string} [extraClass]
     */
    odooBounce: function (extraClass) {
        for (const el of this) {
            el.classList.add('o_catch_attention', extraClass);
            setTimeout(() => el.classList.remove('o_catch_attention', extraClass), 400);
        }
        return this;
    },
    /**
     * Allows to bind events to a handler just as the standard `$.on` function
     * but binds the handler so that it is executed before any already-attached
     * handler for the same events.
     *
     * @see jQuery.on
     */
    prependEvent: function (events, selector, data, handler) {
        this.on.apply(this, arguments);

        events = events.split(' ');
        return this.each(function () {
            var el = this;
            events.forEach((evNameNamespaced) => {
                var evName = evNameNamespaced.split('.')[0];
                var handler = $._data(el, 'events')[evName].pop();
                $._data(el, 'events')[evName].unshift(handler);
            });
        });
    },
    /**
     * @todo Should really be converted to no jQuery and probably even removed
     * from jQuery utilities in master
     * @return {jQuery}
     */
    closestScrollable() {
        const document = this.length ? this[0].ownerDocument : window.document;

        let $el = this;
        while ($el[0] !== document.scrollingElement) {
            if (!$el.length || $el[0] instanceof Document) {
                // Ensure that $().closestScrollable() -> $() and handle the
                // case of elements not attached to the DOM.
                // Also, .parent() used to loop through ancestors can
                // theoretically reach the document if nothing up to the HTML
                // included is not scrollable.
                return $();
            }
            if ($el.isScrollable()) {
                return $el;
            }
            $el = $el.parent();
        }
        return $el;
    },
    /**
     * Adapt the given css property by adding the size of a scrollbar if any.
     * Limitation: only works if the given css property is not already used as
     * inline style for another reason.
     *
     * @param {boolean} [add=true]
     * @param {boolean} [isScrollElement=true]
     * @param {string} [cssProperty='padding-right']
     */
    compensateScrollbar(add = true, isScrollElement = true, cssProperty = 'padding-right') {
        for (const el of this) {
            // Compensate scrollbar
            const scrollableEl = isScrollElement ? el : $(el).parent().closestScrollable()[0];
            const isRTL = scrollableEl.matches(".o_rtl");
            if (isRTL) {
                cssProperty = cssProperty.replace("right", "left");
            }
            el.style.removeProperty(cssProperty);
            if (!add) {
                return;
            }
            const style = window.getComputedStyle(el);
            // Round up to the nearest integer to be as close as possible to
            // the correct value in case of browser zoom.
            const borderLeftWidth = Math.ceil(parseFloat(style.borderLeftWidth.replace('px', '')));
            const borderRightWidth = Math.ceil(parseFloat(style.borderRightWidth.replace('px', '')));
            const bordersWidth = borderLeftWidth + borderRightWidth;
            const newValue = parseInt(style[cssProperty]) + scrollableEl.offsetWidth - scrollableEl.clientWidth - bordersWidth;
            el.style.setProperty(cssProperty, `${newValue}px`, 'important');
        }
    },
    /**
     * @returns {jQuery}
     */
    getScrollingElement(document = window.document) {
        const $baseScrollingElement = $(document.scrollingElement);
        if ($baseScrollingElement.isScrollable()
                && $baseScrollingElement.hasScrollableContent()) {
            return $baseScrollingElement;
        }
        const bodyHeight = $(document.body).height();
        for (const el of document.body.children) {
            // Search for a body child which is at least as tall as the body
            // and which has the ability to scroll if enough content in it. If
            // found, suppose this is the top scrolling element.
            if (bodyHeight - el.scrollHeight > 1.5) {
                continue;
            }
            const $el = $(el);
            if ($el.isScrollable()) {
                return $el;
            }
        }
        return $baseScrollingElement;
    },
    /**
     * @returns {jQuery}
     */
    getScrollingTarget(contextItem = window.document) {
        // Cannot use `instanceof` because of cross-frame issues.
        const isElement = obj => obj && obj.nodeType === Node.ELEMENT_NODE;
        const isJQuery = obj => obj && ('jquery' in obj);

        const $scrollingElement = isElement(contextItem)
            ? $(contextItem)
            : isJQuery(contextItem)
            ? contextItem
            : $().getScrollingElement(contextItem);
        const document = $scrollingElement[0].ownerDocument;
        return $scrollingElement.is(document.scrollingElement)
            ? $(document.defaultView)
            : $scrollingElement;
    },
    /**
     * @return {boolean}
     */
    hasScrollableContent() {
        return this[0].scrollHeight > this[0].clientHeight;
    },
    /**
     * @returns {boolean}
     */
    isScrollable() {
        if (!this.length) {
            return false;
        }
        const overflow = this.css('overflow-y');
        const el = this[0];
        return overflow === 'auto' || overflow === 'scroll'
            || (overflow === 'visible' && el === el.ownerDocument.scrollingElement);
    },
});

// jQuery functions monkey-patching

// Some magic to ensure scrolltop and animate on html/body animate the top level
// scrollable element even if not html or body.
const originalScrollTop = $.fn.scrollTop;
$.fn.scrollTop = function (value) {
    if (value !== undefined && this.filter('html, body').length) {
        // The caller wants to scroll a set of elements including html and/or
        // body to a specific point -> do that but make sure to add the real
        // top level element to that set of elements if any different is found.
        const $withRealScrollable = this.not('html, body').add($().getScrollingElement(this[0].ownerDocument));
        originalScrollTop.apply($withRealScrollable, arguments);
        return this;
    } else if (value === undefined && this.eq(0).is('html, body')) {
        // The caller wants to get the scroll point of a set of elements, jQuery
        // will return the scroll point of the first one, if it is html or body
        // return the scroll point of the real top level element.
        return originalScrollTop.apply($().getScrollingElement(this[0].ownerDocument), arguments);
    }
    return originalScrollTop.apply(this, arguments);
};
const originalAnimate = $.fn.animate;
$.fn.animate = function (properties, ...rest) {
    const props = Object.assign({}, properties);
    if ('scrollTop' in props && this.filter('html, body').length) {
        // The caller wants to scroll a set of elements including html and/or
        // body to a specific point -> do that but make sure to add the real
        // top level element to that set of elements if any different is found.
        const $withRealScrollable = this.not('html, body').add($().getScrollingElement(this[0].ownerDocument));
        originalAnimate.call($withRealScrollable, {'scrollTop': props['scrollTop']}, ...rest);
        delete props['scrollTop'];
    }
    if (!Object.keys(props).length) {
        return this;
    }
    return originalAnimate.call(this, props, ...rest);
};
