/** @odoo-module **/

import { Component, useRef, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class FaceRecognitionComponent extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.videoRef = useRef("video");
        this.canvasRef = useRef("canvas");

        this.startCamera();
    }

    startCamera() {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                this.videoRef.el.srcObject = stream;
                this.videoRef.el.play();
            })
            .catch(error => {
                this.notification.add("Error accessing the camera: " + error.message, { type: "danger" });
            });
    }

    captureImage() {
        const canvas = this.canvasRef.el;
        const context = canvas.getContext('2d');
        context.drawImage(this.videoRef.el, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL('image/png');
    }

    async recognizeFace() {
        const imageData = this.captureImage();
        try {
            const result = await this.rpc({
                model: 'dms.file',
                method: 'recognize_face',
                args: [imageData],
            });
            if (result) {
                this.notification.add('User recognized: ' + result, { type: "success" });
            } else {
                this.notification.add("User not recognized", { type: "danger" });
            }
            this.dialogService.close();
        } catch (error) {
            this.notification.add("Error during face recognition: " + error.message, { type: "danger" });
        }
    }
}

FaceRecognitionComponent.components = {

};
FaceRecognitionComponent.template = xml`
<div>
    <video ref="video" width="640" height="480" autoplay></video>
    <canvas ref="canvas" width="640" height="480" style="display:none;"></canvas>
    <button t-on-click="recognizeFace">Recognize Face</button>
</div>
`;
registry.category("lazy_components").add("FaceRecognitionComponent", FaceRecognitionComponent);
