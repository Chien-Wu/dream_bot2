"""
Dependency injection container for Dream Line Bot.
Manages service instantiation and dependencies.
"""
from typing import Dict, Type, TypeVar, Callable, Any
import inspect

from src.utils import setup_logger


T = TypeVar('T')
logger = setup_logger(__name__)


class Container:
    """Simple dependency injection container."""
    
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
    
    def register_singleton(self, interface: Type[T], implementation: Type[T] = None) -> None:
        """
        Register a singleton service.
        
        Args:
            interface: Interface/abstract class type
            implementation: Concrete implementation class
        """
        impl = implementation or interface
        self._singletons[interface] = impl
        logger.debug(f"Registered singleton: {interface.__name__} -> {impl.__name__}")
    
    def register_transient(self, interface: Type[T], implementation: Type[T] = None) -> None:
        """
        Register a transient service (new instance each time).
        
        Args:
            interface: Interface/abstract class type  
            implementation: Concrete implementation class
        """
        impl = implementation or interface
        self._services[interface] = impl
        logger.debug(f"Registered transient: {interface.__name__} -> {impl.__name__}")
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """
        Register a factory function for a service.
        
        Args:
            interface: Interface/abstract class type
            factory: Factory function that returns instance
        """
        self._factories[interface] = factory
        logger.debug(f"Registered factory: {interface.__name__}")
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """
        Register a pre-created instance.
        
        Args:
            interface: Interface/abstract class type
            instance: Pre-created instance
        """
        self._services[interface] = instance
        logger.debug(f"Registered instance: {interface.__name__}")
    
    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve a service by its interface.
        
        Args:
            interface: Interface/abstract class type to resolve
            
        Returns:
            Service instance
            
        Raises:
            ValueError: If service is not registered
        """
        # Check if it's a factory
        if interface in self._factories:
            return self._factories[interface]()
        
        # Check if it's a singleton
        if interface in self._singletons:
            if interface not in self._services:
                # Create singleton instance
                impl_class = self._singletons[interface]
                instance = self._create_instance(impl_class)
                self._services[interface] = instance
            return self._services[interface]
        
        # Check if it's a transient or instance
        if interface in self._services:
            service = self._services[interface]
            if inspect.isclass(service):
                # Create new instance for transient
                return self._create_instance(service)
            else:
                # Return registered instance
                return service
        
        raise ValueError(f"Service {interface.__name__} is not registered")
    
    def _create_instance(self, cls: Type[T]) -> T:
        """
        Create instance with automatic dependency injection.
        
        Args:
            cls: Class to instantiate
            
        Returns:
            Class instance with dependencies injected
        """
        try:
            # Get constructor signature
            sig = inspect.signature(cls.__init__)
            params = {}
            
            # Resolve constructor dependencies
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                    
                if param.annotation == param.empty:
                    continue
                    
                # Handle string annotations (forward references)
                annotation = param.annotation
                if isinstance(annotation, str):
                    # Skip string annotations - they can't be resolved by the container
                    if param.default == param.empty:
                        logger.warning(f"Cannot resolve string annotation '{annotation}' for {cls.__name__}")
                    continue
                
                # Try to resolve the dependency
                try:
                    params[param_name] = self.resolve(annotation)
                except ValueError:
                    # If dependency not found, check if param has default
                    if param.default == param.empty:
                        logger.warning(f"Cannot resolve dependency {annotation.__name__} for {cls.__name__}")
                        continue
            
            instance = cls(**params)
            logger.debug(f"Created instance: {cls.__name__}")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to create instance of {cls.__name__}: {e}")
            raise


# Global container instance
container = Container()