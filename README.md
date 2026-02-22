SmartSales - API de Backend
Este repositorio contiene el núcleo lógico y de datos del ecosistema SmartSales. Es una API REST desarrollada en Python que centraliza las operaciones de un sistema de e-commerce moderno, integrando procesamiento de pagos y análisis predictivo.

Funcionalidades Principales
Motor de Predicción de Ventas: Implementación de un modelo de Machine Learning (Random Forest) para analizar tendencias históricas y proyectar la demanda de productos.

Procesamiento de Pagos: Integración con la API de Stripe para la gestión segura de transacciones, flujos de checkout y manejo de webhooks.

Arquitectura Desacoplada: Diseñado para servir datos de forma eficiente a clientes web (React) y móviles, manteniendo la lógica de negocio separada de la interfaz de usuario.

Gestión de Inteligencia de Negocios: Endpoints especializados en la generación de métricas de rendimiento y reportes de ventas en tiempo real.

Stack Técnico
Lenguaje: Python

Framework: Django / Django REST Framework.

Data Science: Scikit-learn (Random Forest), Pandas.

Pagos: Stripe Python SDK.

Base de Datos: Supabase - PostgreSQL.
