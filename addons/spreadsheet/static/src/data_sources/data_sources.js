/** @odoo-module */

import { LoadableDataSource } from "./data_source";
import { MetadataRepository } from "./metadata_repository";

import { EventBus } from "@odoo/owl";

/** *
 * @typedef {object} DataSourceServices
 * @property {MetadataRepository} metadataRepository
 * @property {import("@web/core/orm_service")} orm
 * @property {() => void} notify
 *
 * @typedef {new (services: DataSourceServices, params: object) => any} DataSourceConstructor
 */

export class DataSources extends EventBus {
    /**
     * @param {import("@web/env").OdooEnv} env
     */
    constructor(env) {
        super();
        this._orm = env.services.orm.silent;
        this._metadataRepository = new MetadataRepository(env);
        this._metadataRepository.addEventListener("labels-fetched", () => this.notify());
        /** @type {Object.<string, any>} */
        this._dataSources = {};
        this.pendingPromises = new Set();
    }

    /**
     * Create a new data source but do not register it.
     *
     * @param {DataSourceConstructor} cls Class to instantiate
     * @param {object} params Params to give to data source
     *
     * @returns {any}
     */
    create(cls, params) {
        return new cls(
            {
                orm: this._orm,
                metadataRepository: this._metadataRepository,
                notify: () => this.notify(),
                notifyWhenPromiseResolves: this.notifyWhenPromiseResolves.bind(this),
                cancelPromise: (promise) => this.pendingPromises.delete(promise),
            },
            params
        );
    }

    /**
     * Create a new data source and register it with the following id.
     *
     * @param {string} id
     * @param {DataSourceConstructor} cls Class to instantiate
     * @param {object} params Params to give to data source
     *
     * @returns {any}
     */
    add(id, cls, params) {
        this._dataSources[id] = this.create(cls, params);
        return this._dataSources[id];
    }

    async load(id, reload = false) {
        const dataSource = this.get(id);
        if (dataSource instanceof LoadableDataSource) {
            await dataSource.load({ reload });
        }
    }

    /**
     * Retrieve the data source with the following id.
     *
     * @param {string} id
     *
     * @returns {any}
     */
    get(id) {
        return this._dataSources[id];
    }

    /**
     * Check if the following is correspond to a data source.
     *
     * @param {string} id
     *
     * @returns {boolean}
     */
    contains(id) {
        return id in this._dataSources;
    }

    /**
     * @private
     * @param {Promise<unknown>} promise
     */
    async notifyWhenPromiseResolves(promise) {
        this.pendingPromises.add(promise);
        await promise
            .then(() => {
                this.pendingPromises.delete(promise);
                this.notify();
            })
            .catch(() => {
                this.pendingPromises.delete(promise);
                this.notify();
            });
    }

    /**
     * Notify that a data source has been updated. Could be useful to
     * request a re-evaluation.
     */
    notify() {
        if (this.pendingPromises.size) {
            if (!this.nextTriggerTimeOutId) {
                // evaluates at least every 10 seconds, even if there are pending promises
                // to avoid blocking everything if there is a really long request
                this.nextTriggerTimeOutId = setTimeout(() => {
                    this.nextTriggerTimeOutId = undefined;
                    if (this.pendingPromises.size) {
                        this.trigger("data-source-updated");
                    }
                }, 10000);
            }
            return;
        }
        this.trigger("data-source-updated");
    }

    async waitForAllLoaded() {
        await Promise.all(
            Object.values(this._dataSources).map(
                (ds) => ds instanceof LoadableDataSource && ds.load()
            )
        );
    }
}
