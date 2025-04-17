/** @odoo-module **/

const {useRef, onPatched,onRendered,onMounted,onWillPatch } = owl;
import { DiscussSidebarCategories } from "@mail/discuss/core/web/discuss_sidebar_categories";
import { patch } from "@web/core/utils/patch";

patch(DiscussSidebarCategories.prototype, {
     filteredThreads(category) {
         const threads = super.filteredThreads(...arguments)
         return threads.filter((thread) => {return thread.is_pinned})
    }
});
