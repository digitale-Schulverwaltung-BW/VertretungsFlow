<?php
/**
 * Shortcode-Handler für AbsenzFlow
 */

class AbsenzFlow_Shortcode {
    
    private static $instance = null;
    
    public static function get_instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        add_shortcode('absenzflow', array($this, 'render_shortcode'));
        add_action('wp_enqueue_scripts', array($this, 'enqueue_assets'));
    }
    
    /**
     * Enqueue Scripts und Styles
     */
    public function enqueue_assets() {
        // Prüfe ob Shortcode auf Seite vorhanden
        if (!is_singular() || !has_shortcode(get_post()->post_content, 'absenzflow')) {
            return;
        }
        
        // React und ReactDOM von CDN
        wp_enqueue_script(
            'react',
            'https://unpkg.com/react@18/umd/react.production.min.js',
            array(),
            '18.0.0',
            true
        );
        
        wp_enqueue_script(
            'react-dom',
            'https://unpkg.com/react-dom@18/umd/react-dom.production.min.js',
            array('react'),
            '18.0.0',
            true
        );
        
        // AbsenzFlow React App
        wp_enqueue_script(
            'absenzflow-app',
            ABSENZFLOW_PLUGIN_URL . 'build/index.js',
            array('react', 'react-dom'),
            ABSENZFLOW_VERSION,
            true
        );
        
        // CSS
        wp_enqueue_style(
            'absenzflow-styles',
            ABSENZFLOW_PLUGIN_URL . 'build/index.css',
            array(),
            ABSENZFLOW_VERSION
        );
        
        // Config für React App
        $options = get_option('absenzflow_options');
        $current_user = wp_get_current_user();

        $config = array(
            'apiUrl' => isset($options['api_url']) ? $options['api_url'] : '',
            'useProxy' => true, // Use WordPress proxy to avoid HTTPS/HTTP mixed content
            'proxyUrl' => rest_url('absenzflow/v1/proxy'),
            'user' => array(
                'id' => $current_user->ID,
                'username' => $current_user->user_login,
                'email' => $current_user->user_email,
                'displayName' => $current_user->display_name,
                'role' => get_user_meta($current_user->ID, 'absenzflow_role', true) ?: 'teacher'
            )
        );

        wp_localize_script('absenzflow-app', 'absenzflowConfig', $config);
    }
    
    /**
     * Render Shortcode
     */
    public function render_shortcode($atts) {
        // User muss eingeloggt sein
        if (!is_user_logged_in()) {
            return '<div class="absenzflow-error">Bitte melden Sie sich an, um AbsenzFlow zu nutzen.</div>';
        }
        
        // API URL muss konfiguriert sein
        $options = get_option('absenzflow_options');
        if (empty($options['api_url'])) {
            if (current_user_can('manage_options')) {
                return '<div class="absenzflow-error">Bitte konfigurieren Sie die API-URL in den <a href="' . admin_url('admin.php?page=absenzflow-settings') . '">Einstellungen</a>.</div>';
            }
            return '<div class="absenzflow-error">Das System ist noch nicht konfiguriert. Bitte wenden Sie sich an einen Administrator.</div>';
        }
        
        // Container für React App
        return '<div id="absenzflow-root"></div>';
    }
}
