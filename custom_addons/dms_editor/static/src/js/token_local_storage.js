/** @odoo-module */

import dom from '@web/legacy/js/core/dom';
import publicWidget from '@web/legacy/js/public/public_widget';
import { browser } from "@web/core/browser/browser";

publicWidget.registry.login = publicWidget.Widget.extend({
    selector: '.oe_login_form',
    events: {
        'submit': '_onSubmit',
    },

    //-------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    /**
     * Prevents the user from crazy clicking:
     * Gives the button a loading effect if preventDefault was not already
     * called and modifies the preventDefault function of the event so that the
     * loading effect is removed if preventDefault() is called in a following
     * customization.
     *
     * @private
     * @param {Event} ev
     */
    _onSubmit(ev) {
        if (!ev.isDefaultPrevented()) {
            const btnEl = ev.currentTarget.querySelector('button[type="submit"]');
            const email = ev.currentTarget.querySelector('input[name="login"]');
            const removeLoadingEffect = dom.addButtonLoadingEffect(btnEl);
            const oldPreventDefault = ev.preventDefault.bind(ev);
            ev.preventDefault = () => {
                removeLoadingEffect();
                oldPreventDefault();
            };
            const login = email.value;
            // Endpoint call
            const data = {
                "email": login,
                "lType": "filesdna",
                "platform": "web",
                "type": "user" 
            }; 
            
            fetch('https://backend-dev.filesdna.com/api/user/odoo-login', 
                {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                console.log(result)
                browser.localStorage.setItem("id_token", result.token);
                this._updateUserToken(result.token);
            })
            .catch(error => {
                console.error('Error:', error);
            })
            .finally(() => {
                removeLoadingEffect(); 
            });
        }
    },

   
    
});
