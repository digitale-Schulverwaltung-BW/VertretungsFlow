<?php
/**
 * API Proxy für sichere Backend-Kommunikation
 * Verhindert dass API-Credentials im Frontend exposed werden
 */

class AbsenzFlow_API_Proxy {
    
    private static $instance = null;
    
    public static function get_instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        add_action('rest_api_init', array($this, 'register_routes'));
        add_filter('rest_authentication_errors', array($this, 'allow_cookie_auth'));
    }

    /**
     * Allow cookie authentication for our endpoint
     */
    public function allow_cookie_auth($result) {
        // If already authenticated, return early
        if ($result === true || is_wp_error($result)) {
            return $result;
        }

        // Check if this is our endpoint
        if (strpos($_SERVER['REQUEST_URI'], '/absenzflow/v1/proxy') !== false) {
            // Check if user is logged in via WordPress session
            if (is_user_logged_in()) {
                // Allow cookie authentication for this endpoint
                return true;
            }
            // Debug: log why auth failed
            error_log('AbsenzFlow: Cookie auth failed - user not logged in. User ID: ' . get_current_user_id());
        }

        return $result;
    }
    
    /**
     * Registriert REST API Routes
     */
    public function register_routes() {
        // Proxy Route
        register_rest_route('absenzflow/v1', '/proxy', array(
            'methods' => 'POST',
            'callback' => array($this, 'proxy_request'),
            'permission_callback' => 'is_user_logged_in', // WordPress handles cookie auth + nonce validation
            'args' => array(
                'method' => array('required' => true),
                'endpoint' => array('required' => true),
            )
        ));
    }
    
    /**
     * Proxy Request zum Backend
     */
    public function proxy_request($request) {
        $options = get_option('absenzflow_options');
        $api_url = $options['api_url'];
        $api_secret = isset($options['api_secret']) ? $options['api_secret'] : '';

        if (empty($api_url)) {
            return new WP_Error('no_api_url', 'API URL nicht konfiguriert', array('status' => 500));
        }

        if (empty($api_secret)) {
            return new WP_Error('no_api_secret', 'API Secret nicht konfiguriert', array('status' => 500));
        }

        // Request-Daten
        $method = $request->get_param('method');
        $endpoint = $request->get_param('endpoint');
        $body = $request->get_param('body');
        $params = $request->get_param('params');
        $token = $request->get_param('token');

        // Request an Backend
        $url = rtrim($api_url, '/') . '/' . ltrim($endpoint, '/');

        // Query params für GET-Requests
        if (!empty($params) && is_array($params)) {
            $url = add_query_arg($params, $url);
        }

        // Current WordPress user
        $current_user = wp_get_current_user();

        $args = array(
            'method' => strtoupper($method),
            'headers' => array(
                'Content-Type' => 'application/json',
                'X-WordPress-Secret' => $api_secret,
                'X-WordPress-User' => $current_user->user_login
            ),
            'timeout' => 30,
            'sslverify' => false // Allow self-signed certs in development
        );

        // JWT Token hinzufügen falls vorhanden (für direkte Backend-Auth)
        if (!empty($token)) {
            $args['headers']['Authorization'] = 'Bearer ' . $token;
        }

        // Body hinzufügen bei POST/PUT/PATCH
        if (in_array(strtoupper($method), array('POST', 'PUT', 'PATCH')) && !empty($body)) {
            $args['body'] = json_encode($body);
        }

        // Request ausführen
        $response = wp_remote_request($url, $args);

        if (is_wp_error($response)) {
            return new WP_Error('proxy_error', $response->get_error_message(), array('status' => 500));
        }

        $status_code = wp_remote_retrieve_response_code($response);
        $response_body = wp_remote_retrieve_body($response);

        // Response zurückgeben
        return new WP_REST_Response(
            json_decode($response_body, true),
            $status_code
        );
    }
}
