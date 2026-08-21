import { Component, onMounted, onWillStart, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";

export class CapSeoChat extends Component {
    static template = "cap_website_builder.SeoChat";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.threadRef = useRef("thread");
        this.composerRef = useRef("composer");

        // Everything the screen says about itself is config rather than
        // hardcoded, and the action may override any of it through its params.
        this.config = {
            model: "cap.seo.query",
            showDates: true,
            emptyTitle: _t("Ask about your traffic"),
            emptyHint: _t(
                "Answers come from live Search Console and Analytics data, " +
                "not from the model's own knowledge."
            ),
            placeholder: _t("Ask about your traffic…"),
            pendingLabel: _t("Querying Google and reading the rows…"),
            ...(this.props.action.params || {}),
        };

        this.state = useState({
            conversations: [],
            current: null,       // the loaded conversation, or null for a new one
            messages: [],
            draft: "",
            pending: false,      // a turn is in flight
            models: [],
            // Defaults for a conversation that does not exist server-side yet.
            newDefaults: null,
        });

        onWillStart(async () => {
            await this.loadConversations();
            // Only ask for fields the configured model actually has: seeding a
            // field it does not carry makes create() fail.
            const settingFields = ["ai_model_id"];
            if (this.config.showDates) {
                settingFields.push("date_from", "date_to");
            }
            const [models, defaults] = await Promise.all([
                this.orm.searchRead("cap.ai.model", [], ["name"]),
                this.orm.call(this.config.model, "default_get", [settingFields]),
            ]);
            this.state.models = models;
            this.state.newDefaults = {
                ai_model_id: defaults.ai_model_id || false,
            };
            if (this.config.showDates) {
                this.state.newDefaults.date_from = defaults.date_from || "";
                this.state.newDefaults.date_to = defaults.date_to || "";
            }
            if (this.state.conversations.length) {
                await this.openConversation(this.state.conversations[0].id);
            }
        });

        onMounted(() => this.focusComposer());
    }

    // ------------------------------------------------------------------
    // Data
    // ------------------------------------------------------------------
    async loadConversations() {
        this.state.conversations = await this.orm.searchRead(
            this.config.model, [], ["name", "last_activity", "message_count"],
            { limit: 100, order: "last_activity desc" }
        );
    }

    async openConversation(id) {
        // load_chat returns one dict, not a list - it is ensure_one'd.
        const data = await this.orm.call(this.config.model, "load_chat", [[id]]);
        this.state.current = data;
        this.state.messages = data.messages || [];
        this.scrollToBottom();
        this.focusComposer();
    }

    startNewChat() {
        this.state.current = null;
        this.state.messages = [];
        this.state.draft = "";
        this.focusComposer();
    }

    /** The settings shown in the header: the conversation's, or the defaults. */
    get settings() {
        return this.state.current || this.state.newDefaults || {};
    }

    /** Clicking anywhere in a date field opens the calendar, not just the
     *  tiny indicator icon. */
    openPicker(event) {
        if (event.target.showPicker) {
            try {
                event.target.showPicker();
            } catch {
                // Some browsers only allow showPicker() on a trusted gesture;
                // the field still works by typing.
            }
        }
    }

    async updateSetting(field, value) {
        if (field.endsWith("_id")) {
            value = value ? parseInt(value, 10) : false;
        }
        if (this.state.current) {
            await this.orm.write(this.config.model, [this.state.current.id],
                { [field]: value });
            this.state.current[field] = value;
        } else {
            this.state.newDefaults[field] = value;
        }
    }

    // ------------------------------------------------------------------
    // Sending
    // ------------------------------------------------------------------
    async sendMessage() {
        const text = this.state.draft.trim();
        if (!text || this.state.pending) {
            return;
        }
        this.state.pending = true;
        this.state.draft = "";
        this.resizeComposer();

        // Show the question immediately; the two AI calls take a while.
        this.state.messages.push({
            id: `pending-${Date.now()}`,
            role: "user",
            body: `<p>${escapeHtml(text)}</p>`,
        });
        this.scrollToBottom();

        try {
            let conversationId = this.state.current && this.state.current.id;
            if (!conversationId) {
                conversationId = await this.orm.create(
                    this.config.model, [{ ...this.state.newDefaults }]
                ).then((ids) => ids[0]);
            }
            const created = await this.orm.call(
                this.config.model, "action_send_message", [[conversationId], text]
            );
            // Drop the optimistic bubble; the server's copies replace it.
            this.state.messages.pop();
            this.state.messages.push(...created);

            if (!this.state.current || this.state.current.id !== conversationId) {
                await this.openConversation(conversationId);
            }
            await this.loadConversations();
        } catch (error) {
            this.state.messages.pop();
            this.state.draft = text;
            throw error;
        } finally {
            this.state.pending = false;
            this.scrollToBottom();
            this.focusComposer();
        }
    }

    onKeydown(event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    }

    onInput(event) {
        this.state.draft = event.target.value;
        this.resizeComposer();
    }

    // ------------------------------------------------------------------
    // View helpers
    // ------------------------------------------------------------------
    body(message) {
        return markup(message.body || "");
    }

    toggleQuery(message) {
        message.showQuery = !message.showQuery;
    }

    resizeComposer() {
        const node = this.composerRef.el;
        if (node) {
            node.style.height = "auto";
            node.style.height = `${Math.min(node.scrollHeight, 200)}px`;
        }
    }

    focusComposer() {
        setTimeout(() => this.composerRef.el && this.composerRef.el.focus());
    }

    scrollToBottom() {
        setTimeout(() => {
            const node = this.threadRef.el;
            if (node) {
                node.scrollTop = node.scrollHeight;
            }
        });
    }

    get placeholder() {
        return this.config.placeholder;
    }
}

function escapeHtml(text) {
    const node = document.createElement("div");
    node.textContent = text;
    return node.innerHTML;
}

registry.category("actions").add("cap_seo_chat", CapSeoChat);
