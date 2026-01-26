from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.models import OrderTask
from api.serializers.order_task import (
    OrderTaskSerializer,
    OrderTaskCompleteSerializer,
    OrderTaskStartSerializer,
)

class OrderTaskViewSet(viewsets.ModelViewSet):
    queryset = OrderTask.objects.all()
    serializer_class = OrderTaskSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        task = self.get_object()

        serializer = OrderTaskCompleteSerializer(task, data={"status": "Completed"}, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": "Task completed successfully."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        task = self.get_object()

        serializer = OrderTaskStartSerializer(task, data={"status": "In Progress"}, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": "Task started successfully."}, status=status.HTTP_200_OK)