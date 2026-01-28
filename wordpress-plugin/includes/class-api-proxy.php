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
    }
    
    /**
     * Registriert REST API Routes
     */
    public function register_routes() {
        // Proxy Route
        register_rest_route('absenzflow/v1', '/proxy', array(
            'methods' => 'POST',
            'callback' => array($this, 'proxy_request'),
            'permission_callback' => array($this, 'check_permission')
        ));
    }
    
    /**
     * Check Permission
     */
    public function check_permission() {
        return is_user_logged_in();
    }
    
    /**
     * Proxy Request zum Backend
     */
    public function proxy_request($request) {
        $options = get_option('absenzflow_options');
        $api_url = $options['api_url'];
        
        if (empty($api_url)) {
            return new WP_Error('no_api_url', 'API URL nicht konfiguriert', array('status' => 500));
        }
        
        // Request-Daten
        $method = $request->get_param('method');
        $endpoint = $request->get_param('endpoint');
        $body = $request->get_param('body');
        $token = $request->get_param('token');
        
        // Request an Backend
        $url = rtrim($api_url, '/') . '/' . ltrim($endpoint, '/');
        
        $args = array(
            'method' => strtoupper($method),
            'headers' => array(
                'Content-Type' => 'application/json'
            ),
            'timeout' => 30
        );
        
        // JWT Token hinzufügen falls vorhanden
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
        $body = wp_remote_retrieve_body($response);
        
        // Response zurückgeben
        return new WP_REST_Response(
            json_decode($body, true),
            $status_code
        );
    }
}
