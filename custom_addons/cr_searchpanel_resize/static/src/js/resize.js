/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { onMounted } from "@odoo/owl";

patch(SearchPanel.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => this.makeResizable()); // Run after component is mounted
    },

    makeResizable() {
        const searchPanel = document.querySelector(".o_search_panel"); // Get the panel dynamically
        if (!searchPanel) return;

        // Prevent adding multiple resize handles
        if (searchPanel.querySelector(".search-panel-resize-handle")) return;

        // Create a resize handle
        let resizeHandle = document.createElement("div");
        resizeHandle.classList.add("search-panel-resize-handle");
        searchPanel.appendChild(resizeHandle);

        let startX, startWidth;

        resizeHandle.addEventListener("mousedown", (event) => {
            event.preventDefault();
            startX = event.clientX;
            startWidth = searchPanel.offsetWidth;

            document.addEventListener("mousemove", onMouseMove);
            document.addEventListener("mouseup", onMouseUp);
        });

        const onMouseMove = (event) => {
            let newWidth = startWidth + (event.clientX - startX);
            newWidth = Math.max(150, Math.min(2500, newWidth)); // Set min and max width
            searchPanel.style.width = `${newWidth}px`;
        };

        const onMouseUp = () => {
            document.removeEventListener("mousemove", onMouseMove);
            document.removeEventListener("mouseup", onMouseUp);
        };
    }
});
