#include <cstdio>

__global__ void add(const float *a, const float *b, float *c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) c[i] = a[i] + b[i];
}

int main() {
    const int n = 1 << 20;
    float *a, *b, *c;
    cudaMallocManaged(&a, n * sizeof(float));
    cudaMallocManaged(&b, n * sizeof(float));
    cudaMallocManaged(&c, n * sizeof(float));
    for (int i = 0; i < n; i++) { a[i] = 1.0f; b[i] = 2.0f; }
    add<<<(n + 255) / 256, 256>>>(a, b, c, n);
    cudaDeviceSynchronize();
    printf("c[0]=%.1f c[n-1]=%.1f (esperado 3.0)\n", c[0], c[n - 1]);
    return c[0] == 3.0f ? 0 : 1;
}
